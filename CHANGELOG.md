## v1.9 Release Notes:

- Fix: widget collection no longer needs to be in the master scene for the addon to find it.
- Fix: All the related functions now search for the collection recursively so the structure of the Widget Collection location doesn't matter.
- Fix: change the mirrorShape function to only display in pose mode to avoid errors.
- Feature: Add auto-updater

## v1.8 Release Notes:

- Fix: updated to work with Blender 2.93/3.0
- Functionality change: If you are editing a Widget that already exists, it now will use the collection where it is actually located rather than trying to find it in the user preferences settings (fixes error if the collection was called something different)
- changed the default collection name and widget names to better match with Rigify (not my preferred naming convention but its better to have more consistency)
- Removed Logger
- Functionality change: I rewrote the way to add the selected object as a widget without having to read and write to a text file
- Fix: If collection is 'excluded' in the outliner it now re-enables it.

## v1.7 Release Notes

- Fix: Allow rename of Addons-Folder
- Fix: Fixed the symmetrize error if the .L or the .R didn't have a widget
- Fix: Symmetrize Operator caused Error when clicking in Object mode
- Fix: Return to Armature: Didn't unselect widget-object before returning to armature
- Fix: Edit Widget: Show only if active bone has a widget
- Feature: Widgets renamed: Gear --> Gear_complex, Root --> Root_1
- Feature: New Widgets: 3 Axes, 6 Axes, Arrow_double_sided, Arrow_head, Chest, Clavicle, Eyes_Target, FK_Limb, Gear_simple,
  Roll, Root_2, Torso
- Feature: New Property: Panel Category
- Feature: New Property: Bone Widget symmetry suffix
- Feature: Add selected Mesh as widget-shape
- Feature: Added Logger

Note: This version was only tested on Windows. Please write to help.bonewidget@gmail.com
if an error occurs on your OS (Please include error message)

## v1.6 Release Notes

- Fixed the "DELETE UNUSED WIDGETS" function (was crashing because the context was wrong)

## v1.5 Release notes

- fixed the symmetrize error if the .L and .R were sharing the same shape and you tried to symmetrize

## v1.4 Release notes

- add function to clear widget from bone
- add operator to show/hide the collections
- add operator that will resync the names of the wdgts to the bones
- add operator to delete unused widgets
- add property to be able to rotate the widgets
- improve the ui
- add some default widgets (line, cube, half cube, circle, gear, triangle)
- fixed bug when 'custom bone transform' is enabled, size is incorrect

## v1.3 Release Notes:

- updated to work with latest 2.8 api
- added user preferences for the widget prefix and the collection name
- doesn't delete old widget when replacing with a new version [resolved]
- it will only match the bone matrix when the armature is at a scale of 1.0 This is because the old id_data used to point to the object, but now it points to the data object. [resolved]
- also doesn't match bone transforms if armature not at 0,0,0 [resolved]
- doesn't work correctly when there is a "custom shape transforms" [resolved]
- match Bone Transforms works when bone is selected but not when the widget is selected [resolved]
- if the widget names end with .001 etc it will throw an error [resolved]
- if no objects are selected it will throw an error [resolved]
