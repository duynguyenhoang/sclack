import urwid
from sclack.store import Store
from sclack.emoji import emoji_codemap
import time
import unicodedata


def get_icon(name):
    return Store.instance.config['icons'][name]


def remove_diacritic(input):
    '''
    Accept a unicode string, and return a normal string (bytes in Python 3)
    without any diacritical marks.
    '''
    return unicodedata.normalize('NFKD', input).encode('ASCII', 'ignore').decode()


class EmotionsWidgetItem(urwid.AttrMap):
    def __init__(self, icon, id):
        markup = [' ', icon]
        self.id = id
        super(EmotionsWidgetItem, self).__init__(
            urwid.SelectableIcon(markup),
            None,
            {
                None: 'active_set_snooze_item',
                'quick_search_presence_active': 'quick_search_active_focus',
            }
        )


class EmotionsWidgetList(urwid.ListBox):
    def __init__(self, items):
        self.body = urwid.SimpleFocusListWalker(items)
        super(EmotionsWidgetList, self).__init__(self.body)


# class EmotionsWidgetList(urwid.GridFlow):
#     def __init__(self, items):
#         self.body = urwid.SimpleFocusListWalker(items)
#         super(EmotionsWidgetList, self).__init__(items, 500, 500, 0, 'left')
#

DELAY_SECOND = 0.3


class EmotionsWidget(urwid.AttrWrap):
    __metaclass__ = urwid.MetaSignals
    signals = ['close_emoji_list', 'assign_emoji']

    def __init__(self, base, event_loop):
        self.event_loop = event_loop

        self.header = urwid.Edit('')
        self.event_loop = event_loop
        lines = []

        for shortcut, icon in emoji_codemap.items():
            lines.append({
                'icon': icon,
                'id': shortcut
            })

        self.original_items = lines
        widgets = [EmotionsWidgetItem(item['icon'], item['id']) for item in self.original_items]
        self.emotion_list = EmotionsWidgetList(widgets)

        snooze_list = urwid.LineBox(
            urwid.Frame(self.emotion_list, header=self.header),
            title='Emoji',
            title_align='left'
        )
        overlay = urwid.Overlay(
            snooze_list,
            base,
            align='center',
            width=('relative', 40),
            valign='middle',
            height=20,
            right=5
        )
        self.last_keypress = (time.time() - DELAY_SECOND, None)
        super(EmotionsWidget, self).__init__(overlay, 'set_snooze_dialog')

    @property
    def filtered_items(self):
        return self.original_items

    @filtered_items.setter
    def filtered_items(self, items):
        self.emotion_list.body[:] = [
            EmotionsWidgetItem(item['icon'], item['id'])
            for item in items
        ]

    def set_filter(self, loop, data):
        text = self.header.get_edit_text()
        if len(text) > 0:
            text = remove_diacritic(text).strip().lower()
            new_items = [
                item for item in self.original_items
                if text == '' or text in remove_diacritic(item['id'].lower())
            ]

            # Sub string
            new_items_sub = [
                item for item in self.original_items
                if text not in new_items and remove_diacritic(item['id'].lower()).find(text) != -1
            ]
            new_items.extend(new_items_sub)

            self.filtered_items = list({v['id']: v for v in new_items}.values())
        else:
            self.filtered_items = self.original_items

    def keypress(self, size, key):
        reserved_keys = ('up', 'down', 'page up', 'page down')
        if key in reserved_keys:
            return super(EmotionsWidget, self).keypress(size, key)
        elif key == 'enter':
            focus = self.emotion_list.body.get_focus()
            if focus[0]:
                urwid.emit_signal(self, 'assign_emoji', focus[0].id)
                urwid.emit_signal(self, 'close_emoji_list')
                return True
        elif key == 'esc':
            focus = self.emotion_list.body.get_focus()
            if focus[0]:
                urwid.emit_signal(self, 'close_emoji_list')
                return True

        self.header.keypress((size[0],), key)

        now = time.time()
        if now - self.last_keypress[0] < DELAY_SECOND and self.last_keypress[1] is not None:
            self.event_loop.remove_alarm(self.last_keypress[1])

        self.last_keypress = (now, self.event_loop.set_alarm_in(DELAY_SECOND, self.set_filter))

