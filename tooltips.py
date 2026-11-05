"""Non-interactive tooltip for the existing editable Tk Text widgets."""
import tkinter as tk
from prompt_help import prompt_spans, tag_at, popup_position


class PromptTooltip:
    def __init__(self, text, translator, target, delay=320):
        self.text, self.translator, self.target, self.delay = text, translator, target, delay
        self.popup = None
        self.job = None
        self.active = None
        self.revision, self.parsed_revision = 0, -1
        self.spans, self.starts, self.offsets = [], [], [0]
        self.utf16 = int(text.tk.call('string', 'length', '😀')) == 2
        text.bind('<Motion>', self.motion, add='+')
        for event in ('<Leave>', '<ButtonPress>', '<KeyPress>', '<MouseWheel>', '<Button-4>', '<Button-5>', '<Configure>', '<FocusOut>'):
            text.bind(event, self.hide, add='+')
        text.bind('<Destroy>', self.destroy, add='+')

    def invalidate(self):
        self.revision += 1
        self.hide()

    def motion(self, event):
        if event.state & 0x100:  # A selection drag must never show a popup.
            self.hide()
            return
        index = self.text.index(f'@{event.x},{event.y}')
        bounds = self.text.bbox(index)
        if not bounds or not (bounds[0] <= event.x < bounds[0]+bounds[2] and bounds[1] <= event.y < bounds[1]+bounds[3]):
            self.hide()
            return
        if self.text.get(index) in ('', '\n', '\r'):
            self.hide()
            return
        if self.parsed_revision != self.revision:
            content = self.text.get('1.0', 'end-1c')
            self.spans = prompt_spans(content)
            self.offsets = [0]
            for pos, ch in enumerate(content):
                if self.utf16 and ord(ch)>0xffff:self.offsets.append(pos)
                self.offsets.append(pos+1)
            self.starts = [s.start for s in self.spans]
            self.parsed_revision = self.revision
        # Cached Tcl-code-unit to Python-character mapping handles emoji
        # without rescanning the prompt on every mouse movement.
        count = self.text.count('1.0', index, 'chars')
        units = count[0] if count else 0
        offset = self.offsets[min(units,len(self.offsets)-1)]
        tag = tag_at(self.spans, offset, self.starts)
        if tag is None:
            self.hide()
            return
        message = self.translator.lookup(tag, self.target)
        key = (tag.start, tag.end, message)
        if key == self.active:
            return
        was_visible = self.popup is not None
        self.hide()
        self.active = key
        x, y = event.x_root, event.y_root
        self.job = self.text.after(70 if was_visible else self.delay, lambda: self.show(message, x, y))

    def show(self, message, x, y):
        self.job = None
        if not self.text.winfo_exists() or not self.text.winfo_ismapped():
            return
        # vroot bounds keep the popup on the available Tk desktop, including
        # negative coordinates when provided by the window system.
        left, top = self.text.winfo_vrootx(), self.text.winfo_vrooty()
        width, height = self.text.winfo_vrootwidth(), self.text.winfo_vrootheight()
        popup = tk.Toplevel(self.text, takefocus=False)
        self.popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        try: popup.attributes('-topmost', True)
        except tk.TclError: pass
        content = message if len(message)<=800 else message[:799]+'…'
        label = tk.Label(popup, text=content, justify='left', wraplength=max(40, min(320, width-24)),
                         background='#fff9df', foreground='#222222', relief='solid', borderwidth=1,
                         padx=8, pady=5, takefocus=False)
        label.pack()
        popup.update_idletasks()
        # Bound very long user-supplied names as well as the popup position.
        if popup.winfo_reqheight() > height-20:
            limit = max(1, int(len(content)*(height-30)/popup.winfo_reqheight())-10)
            label.configure(text=content[:limit]+'…')
            popup.update_idletasks()
        px, py = popup_position(x,y,popup.winfo_reqwidth(),popup.winfo_reqheight(),(left,top,left+width,top+height))
        popup.geometry(f'{px:+d}{py:+d}')
        popup.deiconify()  # Never call focus_set, grab_set, or wait_window.

    def hide(self, event=None):
        job, self.job = self.job, None
        if job is not None:
            try:self.text.after_cancel(job)
            except tk.TclError:pass
        popup, self.popup = self.popup, None
        if popup is not None:
            try:
                if popup.winfo_exists():popup.destroy()
            except tk.TclError:pass
        self.active = None
        # No 'break': all normal Text keyboard/mouse bindings must still run.

    def destroy(self, event=None):
        self.hide()
