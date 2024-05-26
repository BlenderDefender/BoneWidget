# ##### BEGIN GPL LICENSE BLOCK #####
#
# Copyright (C) 2020 Manuel Rais
# manu@g-lul.com

# Created by Manuel Rais and Christophe Seux

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import (
    Collection,
    Context,
    LayerCollection,
    Object
)


from .. import (
    __package__,
    custom_types
)

def get_widget_prefix(context: 'Context') -> str:
    """Get the widget prefix.

    Args:
        context (Context): The current Blender context

    Returns:
        str: The widget prefix
    """
    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__.split(".")[0]].preferences

    prefix = prefs.widget_prefix

    if context.active_object:
        prefix = prefix.replace("{object}", context.active_object.name)

    return prefix


def get_collection_name(context: 'Context') -> str:
    """Get the name of the widget collection.

    Args:
        context (Context): The current Blender context

    Returns:
        str: The name of the widget collection
    """

    prefs: 'custom_types.AddonPreferences' = context.preferences.addons[__package__.split(".")[0]].preferences

    collection_name = prefs.bonewidget_collection_name

    if context.active_object:
        collection_name = collection_name.replace("{object}", context.active_object.name)

    return collection_name


def get_collection(context: 'Context', perform_ops = True) -> 'Collection':
    """Get the collection, where the widget objects are stored.

    Args:
        context (Context): The current Blender context.

    Returns:
        Collection: The collection to store widget objects in.
    """

    bw_collection_name: str = get_collection_name(context)
    # collection = context.scene.collection.children.get(bw_collection_name)
    collection: 'Collection' = recursively_find_layer_collection(
        context.scene.collection, bw_collection_name)
    if collection:  # if it already exists
        return collection

    if not perform_ops:
        return

    collection = bpy.data.collections.get(bw_collection_name)

    if collection:  # if it exists but not linked to scene
        context.scene.collection.children.link(collection)
        return collection

    # create a new collection
    collection = bpy.data.collections.new(bw_collection_name)
    context.scene.collection.children.link(collection)
    # hide new collection
    viewlayer_collection = context.view_layer.layer_collection.children[collection.name]
    viewlayer_collection.hide_viewport = True
    return collection

def get_collection_temp(context: 'Context') -> 'LayerCollection':
    bw_collection_name: str = get_collection_name(context)
    return recursively_find_layer_collection(
        context.view_layer.layer_collection, bw_collection_name)


def get_view_layer_collection(context: 'Context', widget: 'Object' = None) -> 'LayerCollection':
    """Get the view layer collection of the widget object.

    Args:
        context (Context): The current Blender context.
        widget (Object, optional): The widget of which the view layer collection should be searched. Defaults to None.

    Returns:
        LayerCollection: The view layer collection of the widget object.
    """

    widget_collection: 'Collection' = bpy.data.objects[widget.name].users_collection[0]
    active_layer_collection: 'LayerCollection' = context.view_layer.layer_collection

    # Find the widget collection in the current view layer
    layer_collection: 'LayerCollection' = recursively_find_layer_collection(
        active_layer_collection, widget_collection.name)

    # Make sure the widget collection is not hidden on a data level
    widget_collection.hide_viewport = False

    context.view_layer.active_layer_collection = layer_collection

    # Make sure the widget collection isn't excluded in the view layer, so it can be edited
    layer_collection.exclude = False

    context.view_layer.active_layer_collection = active_layer_collection

    return layer_collection


def recursively_find_layer_collection(layer_collection: 'Collection', collection_name: str) -> 'Collection':
    """Recursively find a collection with a specified collection name.

    Args:
        layer_collection (Collection): The collection to start searching from.
        collection_name (str): The name of the searched collection.

    Returns:
        Collection: The collection that has been searched for.
    """

    found: 'Collection' = None

    if layer_collection.name == collection_name:
        return layer_collection

    for layer in layer_collection.children:
        found = recursively_find_layer_collection(layer, collection_name)
        if found:
            return found
