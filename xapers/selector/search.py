import subprocess
import urwid

from xapers.database import Database
from xapers.documents import Document

class DocListItem(urwid.WidgetWrap):
    def __init__(self, doc):
        self.doc = doc
        self.percent = doc.matchp
        self.docid = self.doc.get_docid()
        self.path = urwid.Text(self.doc.get_fullpaths()[0])
        self.sources = self.doc.get_sources()
        self.tags = urwid.Text(' '.join(self.doc.get_tags()))
        self.url = urwid.Text(self.doc.get_url())
        self.title = urwid.Text(self.doc.get_title())
        self.authors = urwid.Text(self.doc.get_authors())
        self.year = urwid.Text(self.doc.get_year())
        self.data = urwid.Text(self.doc.get_data())

        #self.tag_string = '(%s)' % (' '.join(self.tags))
        self.source_string = '['
        for source,sid in self.sources.items():
            self.source_string += '%s:%s' % (source, sid)
        self.source_string += ']'

        self.c1width = 10

        self.rowHeader = urwid.Columns(
            [('fixed', self.c1width,
              urwid.AttrWrap(
                        urwid.Text('id:%s' % (self.docid)),
                        'head_id',
                        'focus_id')),
             ('fixed', 5,
              urwid.AttrWrap(
                        urwid.Text('%i%%' % (self.percent)),
                        'search_value_default',
                        'focus')),
             ('fixed', len(self.source_string),
              urwid.AttrWrap(
                        urwid.Text('%s' % (self.source_string)),
                        'search_value_default',
                        'focus')),
             ],
            )

        w = urwid.Pile(
            [
                urwid.Divider('-'),
                self.rowHeader,
                self.docfield('tags', value_palette='search_tags'),
                self.docfield('title', value_palette='search_title'),
                self.docfield('authors'),
                self.docfield('year'),
                self.docfield('path'),
                self.docfield('url'),
                self.docfield('data'),
                ]
            ,
            focus_item=1)
        self.__super.__init__(w)

    def docfield(self, field, field_palette=None, value_palette='search_value_default'):
        return urwid.Columns(
            [
                ('fixed', self.c1width,
                 urwid.AttrWrap(
                        urwid.Text(field + ':'),
                        field_palette, 'focus')),
                urwid.AttrWrap(
                    eval('self.' + field),
                    value_palette, 'focus')
                ]
            )

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

class CustomEdit(urwid.Edit):
    __metaclass__ = urwid.signals.MetaSignals
    signals = ['done']

    def keypress(self, size, key):
        if key == 'enter':
            urwid.emit_signal(self, 'done', self.get_edit_text())
            return
        elif key == 'esc':
            urwid.emit_signal(self, 'done', None)
            return

        urwid.Edit.keypress(self, size, key)

class Search(urwid.WidgetWrap):
    def __init__(self, ui, query):
        self.ui = ui
        self.db = Database(self.ui.xdir, writable=False)

        items = []
        for doc in self.db.search(query, limit=20):
            items.append(DocListItem(doc))

        self.listwalker = urwid.SimpleListWalker(items)
        self.listbox = urwid.ListBox(self.listwalker)
        #w = urwid.Frame(urwid.AttrWrap(self.listbox, 'body'))
        #w = urwid.AttrWrap(self.listbox, 'body')
        w = self.listbox
        self.__super.__init__(w)

    def nextEntry(self):
        # listbox.set_focus(listbox.get_next())
        pos = self.listbox.get_focus()[1]
        self.listbox.set_focus(pos + 1)
        # self.listbox.keypress(1, 'down')

    def prevEntry(self):
        pos = self.listbox.get_focus()[1]
        if pos == 0: return
        self.listbox.set_focus(pos - 1)

    def viewEntry(self):
        docid = self.listbox.get_focus()[0].docid
        path = self.listbox.get_focus()[0].doc.get_fullpaths()[0]
        path = path.replace(' ','\ ')
        message = 'opening doc id:%s...' % docid
        self.ui.set_status(message)
        subprocess.call(' '.join(["nohup", "okular", path]) + ' &',
                        shell=True,
                        stdout=open('/dev/null','w'),
                        stderr=open('/dev/null','w'))

    def viewURL(self):
        url = self.listbox.get_focus()[0].doc.get_url()
        message = 'opening url %s...' % url
        self.ui.set_status(message)
        subprocess.call(' '.join(["nohup", "jbrowser", url]) + ' &',
                        shell=True,
                        stdout=open('/dev/null','w'),
                        stderr=open('/dev/null','w'))

    def tag(self, sign):
        # focus = self.listbox.get_focus()[0]
        # tags = focus.tags
        if sign is '+':
            prompt = 'add tag: '
        elif sign is '-':
            prompt = 'remove tag: '
        self.foot = CustomEdit(prompt)
        self.ui.view.set_footer(self.foot)
        self.ui.view.set_focus('footer')
        urwid.connect_signal(self.foot, 'done', self.tag_done, sign)

    def tag_done(self, tag, sign):
        self.ui.view.set_focus('body')
        urwid.disconnect_signal(self, self.foot, 'done', self.tag_done)
        focus = self.listbox.get_focus()[0]
        docid = focus.docid
        db = Database(self.ui.xdir, writable=True)
        doc = db.doc_for_docid(docid)
        if sign is '+':
            msg = "Added tag '%s'" % (tag)
            doc.add_tags(content)
        elif sign is '-':
            msg = "Removed tag '%s'" % (tag)
            doc.remove_tags(tag)
        tags = doc.get_tags()
        focus.tags.set_text(' '.join(tags))
        self.ui.set_status(msg)

    def setField(self, field):
        focus = self.listbox.get_focus()[0]
        element = eval('focus.' + field)
        value = element.get_text()[0]
        self.foot = CustomEdit(field + ': ', edit_text=value)
        self.ui.view.set_footer(self.foot)
        self.ui.view.set_focus('footer')
        urwid.connect_signal(self.foot, 'done', self.setField_done, field)

    def setField_done(self, new, field):
        self.ui.view.set_focus('body')
        urwid.disconnect_signal(self, self.foot, 'done', self.setField_done)
        if new is not None:
            focus = self.listbox.get_focus()[0]
            docid = focus.docid
            # open the database writable and set the new field
            db = Database(self.ui.xdir, writable=True)
            doc = db.doc_for_docid(docid)
            eval('doc.set_' + field + '("' + new + '")')
            # FIXME: update the in-place doc
            # update the display
            element = eval('focus.' + field)
            element.set_text(new)
            msg = "Document id:%s %s updated." % (focus.docid, field)
        else:
            msg = "Nothing done."
        self.ui.set_status(msg)

    def keypress(self, size, key):
        if key is 'n':
            self.nextEntry()
        elif key is 'p':
            self.prevEntry()
        elif key is '+':
            self.tag('+')
        elif key is '-':
            self.tag('-')
        elif key is 'enter':
            self.viewEntry()
        elif key is 'u':
            self.viewURL()
        elif key is 'T':
            self.setField('title')
        elif key is 'A':
            self.setField('authors')
        elif key is 'Y':
            self.setField('year')
        elif key is 'P':
            self.setField('path')
        elif key is 'U':
            self.setField('url')
        else:
            self.ui.keypress(key)