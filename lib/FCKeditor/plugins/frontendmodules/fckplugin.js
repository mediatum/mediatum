/*
 * FCKeditor - The text editor for Internet - http://www.fckeditor.net
 * Copyright (C) 2003-2009 Frederico Caldeira Knabben
 *
 * == BEGIN LICENSE ==
 *
 * Licensed under the terms of any of the following licenses at your
 * choice:
 *
 *  - GNU General Public License Version 2 or later (the "GPL")
 *    http://www.gnu.org/licenses/gpl.html
 *
 *  - GNU Lesser General Public License Version 2.1 or later (the "LGPL")
 *    http://www.gnu.org/licenses/lgpl.html
 *
 *  - Mozilla Public License Version 1.1 or later (the "MPL")
 *    http://www.mozilla.org/MPL/MPL-1.1.html
 *
 * == END LICENSE ==
 *
 * This plugin register Toolbar items to manage frontend modules 
 */

// Our method which is called during initialization of the toolbar.
function FrontendModules()
{
}

// Disable button toggling.
FrontendModules.prototype.GetState = function()
{
	return FCK_TRISTATE_OFF;
}

// Our method which is called on button click.
FrontendModules.prototype.Execute = function()
{
}

// Register the command.
FCKCommands.RegisterCommand('frontendmodules', new FCKDialogCommand('frontendmodules', 'Module', '/modules/init/editor', 500, 350)); 
// Add the button.
var item = new FCKToolbarButton('frontendmodules', 'Frontend Modules');
item.IconPath = FCKPlugins.Items['frontendmodules'].Path + 'frontendmodules.gif';
FCKToolbarItems.RegisterItem('frontendmodules', item);
