#   EMILIA STEVENS

#This code needs to be copy pasted to the Houdini shelf tool

import hou
import os
import uuid
from PySide2.QtWidgets import QMainWindow, QPushButton, QFileDialog

class USDReload:

    def __init__(self):

        #Get current selected nodes
        selected_nodes = hou.selectedNodes()

        #If no nodes are selected
        if len(selected_nodes) == 0:
            print("No nodes selected.")
            return

        #If more than 1 node is selected
        elif len(selected_nodes) > 1:
            print("Multiple nodes selected.")
            return

        else:

            #1 selected node
            self.selected_node = selected_nodes[0]

            #If selected node is not of type null
            if self.selected_node.type().name() != "null":
                print("Selected node is not a null node.")
                return

            else:
                #If the null node does not have the needed parameters of a USD setup
                if (self.selected_node.parm("tag_id") is None) and (self.selected_node.parm("usd_filepath") is None) and  (self.selected_node.parm("usd_connected") is None):
                    print("Selected null node does not have USD parameters.")
                    return

                #Correct null node
                else:

                    #Loading all needed variables from the null node of the USD setup
                    self.controller_tag_id = self.selected_node.parm("tag_id").eval()
                    self.usd_filepath = self.selected_node.parm("usd_filepath").eval()
                    self.usd_connected = self.selected_node.parm("usd_connected").eval()

                    #List with the old camera primitives
                    self.old_camera_list = self.selected_node.parm("camera_list").eval().split("\n")

                    self.reload_nodes()

    def reload_nodes(self):
        """
        Reload all nodes with the tag id of the selected null node USD setup
        :return:
        """

        #Get all nodes in the Houdini file
        all_nodes = hou.node("/obj").allSubChildren()

        #Variables to check if there are lopimportcam nodes in the file with the correct tag id
        #IF YES -> The cameras need to be checked for updates
        lopnet_node_path = None
        sublayer_node = None
        lopimportcam_list = []

        #Going over all nodes
        for node in all_nodes:
            #If a node has the correct comment (tag id)
            if node.userData("usd_setup_tag_id") == self.controller_tag_id:

                #USD IMPORT node needs to be reloaded
                if node.type().name() == "usdimport":
                    node.parm("reload").pressButton()

                #lopnet node path needed for camera check
                elif node.type().name() == "lopnet":
                    # Path to the lopnet is needed to access the cameras
                    lopnet_node_path = node.path()

                #Sublayer node needs to be reloaded
                #Sublayer node needed for camera check
                elif  node.type().name() == "sublayer":
                    node.parm("reload").pressButton()
                    sublayer_node = node

                #All lopimportcam nodes need to be added to the camera list of current lopimportcam nodes
                elif node.type().name() == "lopimportcam":
                    lopimportcam_list.append(node)

        #Correct USD camera setup needs: sublayer, lopnet and a list of all cameras from the previous setup
        if (sublayer_node is not None) and (lopnet_node_path is not None) and (len(lopimportcam_list) != 0):

            self.check_cameras(sublayer_node, lopnet_node_path, lopimportcam_list)

    def check_cameras(self, sublayer_node, lopnet_node_path, lopimportcam_list):
        """
        Check cameras to reference any newly created cameras or remove any deleted cameras
        :param sublayer_node: Sublayer node in the lopnet
        :param lopnet_node_path: Path for the lopnet
        :param lopimportcam_list: List with lopimportcam nodes
        :return:
        """

        #Get the USD stage from the sublayer_node (represents the scene graph of this layer)
        stage = sublayer_node.stage()

        #List of camera paths from the updated USD file
        new_camera_list = []

        #Copy of the old camera paths: If a new camera is in this list, the string is removed from the list in the for loop
        #                               -> camera paths that are still in the list at the end are cameras that are deleted (lopimportcam nodes need to be destroyed)
        copy_old_camera_list = self.old_camera_list

        camera_group = self.find_network_box_with_node(lopimportcam_list[0])

        #x_pos = x position in the network of the last lopimportcam node
        x_pos = lopimportcam_list[-1].position()[0]
        #y_pos = y position in the network of the last lopimportcam node
        y_pos = lopimportcam_list[-1].position()[1]

        y_spacing = -1
        y_pos += y_spacing

        #For all primitives inside the stage:
        #If a primitive is of type "Camera", append its path to the new camera list
        for prim in stage.Traverse():
            if prim.GetTypeName() == "Camera":

                camera_path = str(prim.GetPath())
                new_camera_list.append(camera_path)

                #If the camera path is inside the old_camera_list: remove it from the copy list
                if camera_path in self.old_camera_list:
                    copy_old_camera_list.remove(camera_path)

                #If a camera is not in the old_camera_list -> NEW CAMERA
                else:
                    # Create a new lopimportcamera nodes under /obj
                    obj = hou.node("/obj")

                    # Gets rid of the "/" at the start of the naming
                    first_part, camera_name = camera_path.rsplit("/", 1)

                    # Naming for the node
                    node_name = "lopimport_" + camera_name

                    # Create a lopimportcamera node for each camera_path
                    lopimportcamera_node = obj.createNode("lopimportcam", node_name)

                    self.tag_node(lopimportcamera_node)

                    # The loppath is the path to the lopnet node
                    lopimportcamera_node.parm("loppath").set(lopnet_node_path)
                    # The primitive path is the path in the USD hierarchy to the camera pRimitve
                    lopimportcamera_node.parm("primpath").set(camera_path)

                    # Position nodes inside group in a vertical stack
                    lopimportcamera_node.setPosition(hou.Vector2(x_pos, y_pos))
                    y_pos += y_spacing

                    camera_group.addNode(lopimportcamera_node)

        # Create a null node to add some spacing for the naming
        null_node = hou.node("/obj").createNode("null", "null_for_resizing")
        null_node.setPosition(hou.Vector2(x_pos + 3, y_pos - y_spacing))
        camera_group.addNode(null_node)


        #Fit the group around the nodes
        camera_group.fitAroundContents()
        null_node.destroy()


        #Going over all lopimportcam nodes in the list
        for node in lopimportcam_list:
            #If a node in the lopimportcam_list is in the copy_old_camera_list -> DELETED CAMERA
            if node.parm("primpath").eval() in copy_old_camera_list:
                node.destroy()

        #New camera list parameter for the USD setup null node
        camera_list_string = "\n".join(new_camera_list)

        parm = self.selected_node.parm("camera_list")
        if parm is not None:
            parm.lock(False)
            parm.set(camera_list_string)
            parm.lock(True)
        else:
            print("Parameter 'camera_list' not found.")

    def find_network_box_with_node(self, node):

        if isinstance(node, str):
            node = hou.node(node)
        if node is None:
            raise ValueError("Node not found!")

        parent = node.parent()
        for netbox in parent.networkBoxes():
            if node in netbox.nodes() and (self.selected_node not in netbox.nodes()):
                return netbox
        return None

    def tag_node(self, node):
        """
        Function that adds a comment to the node with the tag id of this USD setup
        :param node: Node where the tag id needs to be added to
        :return:
        """
        node.setUserData("usd_setup_tag_id", self.controller_tag_id)

USDReload()
