import sys
import types
# Ensure a stub 'hou' module exists before pipeline imports it
sys.modules['hou'] = types.ModuleType('hou')

import os
import pytest
import pipeline.hip_manager as hm

# Dummy node class to simulate Houdini nodes
class DummyNode:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.moved = False
        self.layout_called = False
        self._default = True  # Simulate default file SOP existing

    def createNode(self, node_type, node_name):
        # Create a new DummyNode or a DummyFileSop for file SOP
        if node_type == 'file' and node_name == 'import_usd':
            node = DummyFileSop(node_name)
        else:
            node = DummyNode(node_name)
        node.type = node_type
        self.children.append((node_type, node_name, node))
        return node

    def node(self, name):
        if name == "file1" and self._default:
            class Default:
                def __init__(self): self.destroy_called = False
                def destroy(self): self.destroy_called = True
            return Default()
        return None

    def moveToGoodPosition(self):
        self.moved = True

    def layoutChildren(self):
        self.layout_called = True

# Specialized DummyFileSop to provide parm().set() API
class DummyFileSop(DummyNode):
    def __init__(self, name):
        super().__init__(name)
        self.parm_values = {}

    def parm(self, parm_name):
        # Return an object with a .set() method
        class Parm:
            def __init__(self, sop, name):
                self.sop = sop
                self.name = name
            def set(self, val):
                self.sop.parm_values[self.name] = val
        return Parm(self, parm_name)

# Fixture to replace pipeline.hip_manager.hou with fake_hou namespace
@pytest.fixture(autouse=True)
def fake_hou(monkeypatch):
    # Create a fake hou namespace
    fake_hou = types.SimpleNamespace()
    # Simulate hipFile methods
    fake_hipFile = types.SimpleNamespace(
        load=lambda path, suppress_save_prompt=False: setattr(fake_hipFile, 'loaded', path),
        save=lambda path=None: setattr(fake_hipFile, 'saved', path)
    )
    fake_hou.hipFile = fake_hipFile
    # Monkeypatch hou.node to return DummyNode for /obj
    parent_node = DummyNode("/obj")
    fake_hou.node = lambda path: parent_node if path == "/obj" else None

    # Override the module-level hou in pipeline.hip_manager
    monkeypatch.setattr(hm, 'hou', fake_hou)
    return fake_hou

# Test load: missing HIP file raises FileNotFoundError

def test_load_missing_file(tmp_path):
    hip = hm.HoudiniHipManager()
    missing = str(tmp_path / "nope.hip")
    assert not os.path.exists(missing)
    with pytest.raises(FileNotFoundError):
        hip.load(missing)

# Test save: calls hou.hipFile.save with and without path

def test_save_calls_hipfile(tmp_path, fake_hou):
    hip = hm.HoudiniHipManager()
    # save without path
    hip.save()
    assert hasattr(fake_hou.hipFile, 'saved') and fake_hou.hipFile.saved is None
    # save with specific path
    out = str(tmp_path / 'out.hip')
    hip.save(out)
    assert fake_hou.hipFile.saved == out

# Test import_usd: missing USD raises FileNotFoundError

def test_import_usd_missing_file():
    hip = hm.HoudiniHipManager()
    with pytest.raises(FileNotFoundError):
        hip.import_usd("does_not_exist.usd")

# Test import_usd success: creates geo node under /obj and sets file path

def test_import_usd_success(tmp_path, fake_hou):
    usd_path = tmp_path / "test_asset.usd"
    usd_path.write_text("")

    hip = hm.HoudiniHipManager()
    hip.import_usd(str(usd_path))

    # Verify a geo node was created under /obj
    parent = fake_hou.node("/obj")
    geo_children = [child for child in parent.children if child[0] == 'geo']
    assert geo_children, "No geo node created under /obj"

    # Extract the geo node object
    _, _, geo_node = geo_children[0]

    # Within the geo node, find the 'file' SOP
    file_children = [child for child in geo_node.children if child[0] == 'file']
    assert file_children, "No file SOP node created under geo"

    # Extract the file SOP object and check its parm_values
    _, _, file_node = file_children[0]
    assert isinstance(file_node.parm_values, dict), "file_node missing parm_values"
    assert file_node.parm_values.get('file') == str(usd_path), f"Expected parm 'file' to be set to '{usd_path}', got {file_node.parm_values.get('file')}"
