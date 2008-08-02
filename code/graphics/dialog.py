#file: dialog.py
#Copyright (C) 2008 FunnyMan3595
#This file is part of Endgame: Singularity.

#Endgame: Singularity is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation; either version 2 of the License, or
#(at your option) any later version.

#Endgame: Singularity is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Endgame: Singularity; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#This file contains the dialog class.

import bisect
import time
import pygame

import constants
import g
import widget
import text
import button

def causes_remask(data_member):
    """Creates a data member that sets needs_remask to True when changed."""
    return widget.set_on_change(data_member, "needs_remask")

def insort_all(sorted_list, items):
    for item in items:
        bisect.insort(sorted_list, item)

class Dialog(text.Text):
    """A Dialog is a Widget that has its own event loop and can be faded out."""

    top = None # The top-level dialog.

    faded = widget.causes_redraw("_faded")

    _collision_rect = causes_remask("__collision_rect")

    def __init__(self, parent, pos = (.5,.1), size = (1, .9), 
                 anchor = constants.TOP_CENTER, **kwargs):
        super(Dialog, self).__init__(parent, pos, size, anchor, **kwargs)
        self.visible = False
        self.faded = False
        self.has_mask = True
        self.needs_remask = True

        self.needs_timer = None

        self.handlers = {}
        self.key_handlers = {}

        if self.parent == None and self.background_color == (0,0,0,0):
            self.background_color = (0,0,0,255)

    def make_top(self):
        """Makes this dialog be the top-level dialog."""
        if self.parent != None:
            raise ValueError, \
                  "Dialogs with parents cannot be the top-level dialog."
        else:
            Dialog.top = self

    def remake_surfaces(self):
        """Recreates the surfaces that this widget will draw on.  This version
           handles the top-level Dialog via pygame's main surface."""
        super(Dialog, self).remake_surfaces()
        if self.parent == None:
            self.surface = pygame.display.set_mode(self.surface.get_size())

    def make_fade_mask(self):
        """Recreates the fade mask for this dialog.  Override if part of the 
           dialog should remain fully visible, even when not active."""
        mask = pygame.Surface(self.real_size, 0, g.ALPHA)
        mask.fill( (0,0,0,175) )
        return mask

    def get_fade_mask(self):
        """If the dialog needs a remask, calls make_fade_mask.  Otherwise, 
           returns the pre-made fade mask."""
        if self.needs_remask:
            self._fade_mask = self.make_fade_mask()
            self.needs_remask = False
        return self._fade_mask

    fade_mask = property(get_fade_mask)

    def do_mask(self):
        """Greys out the dialog when faded, to make it clear that it's not 
           active."""
        if self.faded:
            self.surface.blit( self.get_fade_mask(), (0,0) )

    def start_timer(self, force = False):
        if self.needs_timer == None:
            self.needs_timer = bool(self.handlers.get(constants.TICK, False))
        if self.needs_timer or force:
            pygame.time.set_timer(pygame.USEREVENT, 1000 / g.FPS)

    def stop_timer(self):
        pygame.time.set_timer(pygame.USEREVENT, 0)

    def reset_timer(self):
        self.stop_timer()
        self.start_timer()

    def show(self):
        """Shows the dialog and enters an event-handling loop."""
        self.visible = True
        self.key_down = None
        self.start_timer()
        while True:
            # Redraw handles rebuilding and redrawing all widgets, as needed.
            Dialog.top.redraw()
            event = pygame.event.wait()
            result = self.handle(event)
            if result != constants.NO_RESULT:
                self.visible = False
                return result
        self.stop_timer()

    def add_handler(self, type, handler, priority = 100):
        """Adds a handler of the given type, with the given priority."""
        bisect.insort( self.handlers.setdefault(type, []), 
                       (priority, handler) )

    def remove_handler(self, type, handler):
        """Removes all instances of the given handler from the given type."""
        self.handlers[type] = [h for h in self.handlers.get(type, [])
                                 if h[1] != handler]

    def add_key_handler(self, key, handler, priority = 100):
        """Adds a key handler to the given key, with the given priority."""
        bisect.insort( self.key_handlers.setdefault(key, []), 
                       (priority, handler) )

    def remove_key_handler(self, key, handler):
        """Removes all instances of the given handler from the given key."""
        self.key_handlers[key] = [h for h in self.handlers.get(key, []) 
                                    if h[1] != handler]

    def handle(self, event):
        """Sends an event through all the applicable handlers, returning
           constants.NO_RESULT if the event goes unhandled or is handled without
           requesting the dialog to exit.  Otherwise, returns the value provided
           by the handler."""
        # Get the applicable handlers.  The handlers lists are all sorted.
        # If more than one handler type is applicable, we use [:] to make a 
        # copy of the first type's list, then insort_all to insert the elements
        # of the other lists in proper sorted order.
        if event.type == pygame.MOUSEMOTION:
            # Compress multiple MOUSEMOTION events into one.
            # Note that the pos will be wrong, so pygame.mouse.get_pos() must
            # be used instead.
            time.sleep(1. / g.FPS)
            pygame.event.clear(pygame.MOUSEMOTION)

            # Generic mouse motion handlers.
            handlers = self.handlers.get(constants.MOUSEMOTION, [])[:]

            # Drag handlers.
            if event.buttons[0]:
                insort_all(handlers, self.handlers.get(constants.DRAG, []))
        elif event.type == pygame.USEREVENT:
            # Clear excess timer ticks.
            pygame.event.clear(pygame.USEREVENT)

            # Timer tick handlers.
            handlers = self.handlers.get(constants.TICK, [])

            # Generate repeated keys.
            if self.key_down:
                self.repeat_counter += 1
                if self.repeat_counter >= 5:
                    self.repeat_counter = 0
                    self.handle(self.key_down)
        elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
            # Generic key event handlers.
            handlers = self.handlers.get(constants.KEY, [])[:]

            if event.type == pygame.KEYDOWN:
                # Generic keydown handlers.
                insort_all(handlers, self.handlers.get(constants.KEYDOWN, []))

                if event.unicode:
                    # Unicode-based keydown handlers for this particular key.
                    insort_all(handlers, self.key_handlers.get(event.unicode, []))

                # Begin repeating keys.
                if self.key_down is not event:
                    self.key_down = event
                    self.repeat_counter = -10
                    self.start_timer(force = True)
            else: # event.type == pygame.KEYUP:
                # Stop repeating keys.
                self.key_down = None
                self.reset_timer()

                # Generic keyup handlers.
                insort_all(handlers, self.handlers.get(constants.KEYUP, []))

                # Unicode-based keyup handling not available.
                # pygame doesn't bother defining .unicode on KEYUP events.

            # Keycode-based handlers for this particular key.
            insort_all(handlers, self.key_handlers.get(event.key, []))
        elif event.type == pygame.MOUSEBUTTONUP:
            # Mouse click handlers.
            handlers = self.handlers.get(constants.CLICK, [])
        elif event.type == pygame.QUIT:
            raise SystemExit
        else:
            handlers = []


        # Feed the event to all the handlers, in priority order.
        for priority, handler in handlers:
            try:
                handler(event)
            except constants.Handled:
                break # If it's been handled, we leave the rest alone.
            except constants.ExitDialog, e:
                # Exiting the dialog.
                if e.args: 
                   # If we're given a return value, we pass it on.
                   return e.args[0]
                else:
                   # Otherwise, exit with a return value of None.
                   return 
    
        # None of the handlers instructed the dialog to close, so we pass that
        # information back up to the event loop.
        return constants.NO_RESULT


class TextDialog(Dialog):
    def __init__(self, parent, pos = (.5,.1), size = (.5,.5),
                 anchor = constants.TOP_CENTER, valign = constants.TOP,
                 shrink_factor = .88, background_color = (0,0,0,128), **kwargs):

        super(TextDialog, self).__init__(parent, pos, size, anchor, 
                                         shrink_factor = shrink_factor,
                                         background_color = background_color,
                                         valign = valign, **kwargs)


class YesNoDialog(TextDialog):
    yes_type = widget.causes_rebuild("_yes_type")
    no_type = widget.causes_rebuild("_no_type")
    def __init__(self, parent, **kwargs):
        self.parent = parent

        self.yes_type = kwargs.pop("yes_type", "yes")
        self.no_type = kwargs.pop("no_type", "no")
        self.invert_enter = kwargs.pop("invert_enter", False)
        self.invert_escape = kwargs.pop("invert_escape", False)

        super(YesNoDialog, self).__init__(parent, **kwargs)

        self.yes_button = button.ExitDialogButton(self, (.1,1), (.3,.1), 
                                                 anchor = constants.BOTTOM_LEFT,
                                                 exit_code = True)

        self.no_button = button.ExitDialogButton(self, (.9,1), (.3,.1), 
                                                anchor = constants.BOTTOM_RIGHT,
                                                exit_code = False)

        self.add_key_handler(pygame.K_RETURN, self.on_return)
        self.add_key_handler(pygame.K_ESCAPE, self.on_escape)

    def rebuild(self):
        super(YesNoDialog, self).rebuild()

        self.yes_button.text = g.buttons[self.yes_type]
        self.yes_button.hotkey = g.buttons[self.yes_type + "_hotkey"]
        self.no_button.text = g.buttons[self.no_type]
        self.no_button.hotkey = g.buttons[self.no_type + "_hotkey"]

    def on_return(self, event):
        if self.invert_enter:
            self.no_button.activated(event)
        else:
            self.yes_button.activated(event)

    def on_escape(self, event):
        if self.invert_escape:
            self.yes_button.activated(event)
        else:
            self.no_button.activated(event)


class MessageDialog(TextDialog):
    ok_type = widget.causes_rebuild("_ok_type")
    def __init__(self, parent, **kwargs):
        self.parent = parent

        self.ok_type = kwargs.pop("ok_type", "ok")

        super(MessageDialog, self).__init__(parent, **kwargs)

        self.ok_button = button.ExitDialogButton(self, (.5,1), (.3,.1), 
                                               anchor = constants.BOTTOM_CENTER)

        self.add_key_handler(pygame.K_RETURN, self.ok_button.activated)
        self.add_key_handler(pygame.K_ESCAPE, self.ok_button.activated)

    def rebuild(self):
        super(MessageDialog, self).rebuild()

        self.ok_button.text = g.buttons[self.ok_type]
        self.ok_button.hotkey = g.buttons[self.ok_type + "_hotkey"]


class TextEntryDialog(TextDialog):
    def __init__(self, parent, size = (.2, .1), **kwargs):
        self.default_text = kwargs.pop("default_text", "")

        super(TextEntryDialog, self).__init__(parent, size = size, **kwargs)

        self.text_field = text.EditableText(self, (.5,1), (1,.5),
                                            borders = constants.ALL, 
                                            base_font = g.font[0],
                                            anchor = constants.BOTTOM_CENTER)

        self.add_key_handler(pygame.K_RETURN, self.return_text)
        self.add_key_handler(pygame.K_ESCAPE, self.return_nothing)

    def show(self):
        self.text_field.text = self.default_text
        self.text_field.cursor_pos = len(self.default_text)
        super(TextEntryDialog, self).show()

    def return_nothing(self, event):
        raise constants.ExitDialog, ""

    def return_text(self, event):
        raise constants.ExitDialog, self.text_field.text