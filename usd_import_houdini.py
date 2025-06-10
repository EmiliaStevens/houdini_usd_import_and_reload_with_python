#   EMILIA STEVENS

#This code needs to be copy pasted to the Houdini shelf tool

import hou
import os
import uuid
from PySide2.QtWidgets import QMainWindow, QPushButton, QFileDialog

class PythonTools(QMainWindow):

    def __init__(self):

        super().__init__()

        # file path to the USD file that will be selected
        self.file_path = ""
        self.controller = None
        #Generate random tag id for this USD setup
        self.controller_tag_id = str(uuid.uuid4())

        #UI setup
        self.setWindowTitle("Get USD File")
        self.setFixedSize(250, 100)

        #Filepath button setup
        set_filepath_button = QPushButton("Set Filepath")
        set_filepath_button.clicked.connect(self.set_location)
        self.setCentralWidget(set_filepath_button)


    def set_location(self, *args):
        """
        Sets the location for the USD file that needs to be imported.
        :param args:
        :return:
        """
        self.file_path, _ = QFileDialog.getOpenFileName(
            None, "Select USD File", "", "USD Files (*.usd *.usda *.usdc)"
        )

        #If no USD file is selected when the file explorer is closed, an error will show on the console and the UI window will close
        if self.file_path == "":
            print("No file was selected.")
            self.close_window()

        else:
            self.close_window()
            obj = hou.node("/obj")
            self.setup_group = obj.createNetworkBox()


            self.node_setup()


    def node_setup(self):

        first_part, file_name = self.file_path.rsplit("/", 1)
        file_name_without_extension, extension = file_name.rsplit(".", 1)
        null_node_connection_name = "usd_import_controller_" + file_name_without_extension

        self.setup_group.setComment(f"{file_name_without_extension.upper()} USD SETUP")


        #Create a null node as reference for the tag id, filepath, and connection
        self.controller = hou.node("/obj").createNode("null", null_node_connection_name)
        self.controller.addSpareParmTuple(
                hou.ToggleParmTemplate("usd_connected", "USD Connected", default_value=True))
        self.controller.addSpareParmTuple(
                hou.StringParmTemplate("usd_filepath", "USD Filepath", 1, default_value=([self.file_path])))
        self.controller.addSpareParmTuple(
            hou.StringParmTemplate("tag_id", "tag_id", 1, default_value=([self.controller_tag_id])))

        self.controller.setPosition(hou.Vector2(-5, -2))
        self.controller.setColor(hou.Color((0.7647, 0.8588, 0.7725)))

        self.setup_group.addNode(self.controller)

        self.create_usd_geometry_setup()
        self.create_usd_camera_setup()

    def tag_node(self, node):
        """
        Function that adds a comment to the node with the tag id of this USD setup
        :param node: Node where the tag id needs to be added to
        :return:
        """
        node.setUserData("usd_setup_tag_id", self.controller_tag_id)

    def create_usd_geometry_setup(self):

        """
        Creates the USD node setup for the geometry of the USD file.
        :return:
        """

        #Create a new geo node under /obj
        obj = hou.node("/obj")
        geo_node = obj.createNode("geo", "usd_geo")

        self.tag_node(geo_node)

        #Create a group to put the usd_geo nod ein
        geo_group = obj.createNetworkBox()
        geo_group.addNode(geo_node)

        #Create a null node to add some spacing for the naming
        null_node = obj.createNode("null", "null_for_resizing")
        null_node.setPosition(hou.Vector2(1.2,0))
        geo_group.addNode(null_node)

        #Fit the group around the nodes
        geo_group.fitAroundContents()
        null_node.destroy()

        #Set position, naming and color of the group
        geo_group.setPosition(hou.Vector2(-5, 0))
        geo_group.setComment("GEOMETRY USD SETUP")
        geo_group.setColor(hou.Color((0.8, 0.8, 0.8)))

        self.setup_group.addNetworkBox(geo_group)


        #Create the import usd node inside the geo node and set the filepath to the chosen USD file
        usd_node = geo_node.createNode("usdimport", "usd_import")
        self.tag_node(usd_node)

        usd_node.parm("filepath1").set(self.file_path)

        #Unpack the USD
        unpack_usd_node = geo_node.createNode("unpackusd::2.0", "usd_unpack")
        self.tag_node(unpack_usd_node)
        unpack_usd_node.parm("output").set(1)
        #Connect 2 nodes
        unpack_usd_node.setInput(0, usd_node)

        #Create an OUT null node
        out_usd_geo_null_node = geo_node.createNode("null", "OUT_USD_GEO")
        self.tag_node(out_usd_geo_null_node)
        out_usd_geo_null_node.setInput(0, unpack_usd_node)

        usd_node.moveToGoodPosition()
        geo_node.layoutChildren()

    def create_usd_camera_setup(self):

        """
        Creates the USD node setup for the cameras of the USD file.
        :return:
        """

        #Create a new lopnet node under /obj
        obj = hou.node("/obj")
        lopnet_node = obj.createNode("lopnet", "usd_lopnet_import_camera")
        self.tag_node(lopnet_node)


        #Create the sublayer node inside the lopnet and set the filepath to the chosen USD file
        sublayer_node = lopnet_node.createNode("sublayer", "usd_sublayer_import")
        self.tag_node(sublayer_node)
        sublayer_node.parm("filepath1").set(self.file_path)

        #Get the USD stage from the sublayer_node (represents the scene graph of this layer)
        stage = sublayer_node.stage()

        camera_paths = []

        #For all primitives inside the stage:
        #If a primitive is of type "Camera", append its path to the list
        for prim in stage.Traverse():
            if prim.GetTypeName() == "Camera":
                camera_paths.append(str(prim.GetPath()))

        #If there are any cameras found, create lopimportcamera nodes for those cameras
        if len(camera_paths) != 0:
            self.create_lopimport_camera_nodes(camera_paths, lopnet_node)
        else:
            lopnet_node.destroy()

    def create_lopimport_camera_nodes(self, list_camera_paths, lopnet_node):
        """
        Creates camera nodes for all cameras in the USD file.
        :param list_camera_paths: Paths of the cameras found in the USD file
        :param lopnet_node: Lopnet node in /obj
        :return:
        """
        camera_list_string = "\n".join(list_camera_paths)

        self.controller.addSpareParmTuple(
            hou.StringParmTemplate("camera_list", "Camera List", 1, default_value=(camera_list_string,))
        )

        #Positioning of the lopnet and lopimportcamera nodes
        x_pos = 0
        y_pos = -1
        y_spacing = -1

        # Create a new lopimportcamera nodes under /obj
        obj = hou.node("/obj")

        #Group for the lopnet and lopimportcamera nodes
        camera_group = obj.createNetworkBox()
        lopnet_node.setPosition(hou.Vector2(0, 0))
        camera_group.addNode(lopnet_node)

        #Path to the lopnet is needed to access the cameras
        lopnet_node_path = lopnet_node.path()

        #Going over all cameras primitives in the list
        for camera_path in list_camera_paths:


            #Gets rid of the "/" at the start of the naming
            first_part, camera_name = camera_path.rsplit("/", 1)

            #Naming for the node
            node_name = "lopimport_" + camera_name

            #Create a lopimportcamera node for each camera_path
            lopimportcamera_node = obj.createNode("lopimportcam", node_name)

            self.tag_node(lopimportcamera_node)

            #The loppath is the path to the lopnet node
            lopimportcamera_node.parm("loppath").set(lopnet_node_path)
            #The primitive path is the path in the USD hierarchy to the camera ptimitve
            lopimportcamera_node.parm("primpath").set(camera_path)

            #Position nodes inside group in a vertical stack
            lopimportcamera_node.setPosition(hou.Vector2(x_pos, y_pos))
            y_pos += y_spacing

            camera_group.addNode(lopimportcamera_node)

        # Create a null node to add some spacing for the naming
        null_node = obj.createNode("null", "null_for_resizing")
        null_node.setPosition(hou.Vector2(x_pos + 3, y_pos/2))
        camera_group.addNode(null_node)


        #Fit the group around the nodes
        camera_group.fitAroundContents()
        null_node.destroy()

        # Set position, naming and color of the group
        camera_group.setPosition(hou.Vector2(0, y_pos - y_spacing))
        camera_group.setComment("CAMERA USD SETUP")
        camera_group.setColor(hou.Color((0.7647, 0.8588, 0.7725)))

        self.setup_group.addNetworkBox(camera_group)
        self.setup_group.fitAroundContents()

        # Lock all parameters of the null node so the user cannot change them
        for parm in self.controller.parms():
            parm.lock(True)


    def close_window(self, *args):

        self.close()

window = PythonTools()
window.show()

