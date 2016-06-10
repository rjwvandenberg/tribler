import urllib

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QAction, QTreeWidgetItem
from TriblerGUI.TriblerActionMenu import TriblerActionMenu
from TriblerGUI.channel_torrent_list_item import ChannelTorrentListItem

from TriblerGUI.defs import PAGE_MY_CHANNEL_OVERVIEW, PAGE_MY_CHANNEL_SETTINGS, PAGE_MY_CHANNEL_TORRENTS, \
    PAGE_MY_CHANNEL_PLAYLISTS, PAGE_MY_CHANNEL_RSS_FEEDS, BUTTON_TYPE_NORMAL, BUTTON_TYPE_CONFIRM, \
    PAGE_MY_CHANNEL_PLAYLIST_EDIT, PAGE_MY_CHANNEL_PLAYLIST_TORRENTS, PAGE_MY_CHANNEL_PLAYLIST_MANAGE
from TriblerGUI.dialogs.confirmationdialog import ConfirmationDialog
from TriblerGUI.playlist_list_item import PlaylistListItem
from TriblerGUI.tribler_request_manager import TriblerRequestManager


class MyChannelPage(QWidget):
    """
    This class is responsible for managing lists and data on the your channel page, including torrents, playlists
    and rss feeds.
    """

    def initialize_my_channel_page(self):
        self.window().create_channel_intro_button.clicked.connect(self.on_create_channel_intro_button_clicked)

        self.window().create_channel_form.hide()

        self.window().my_channel_stacked_widget.setCurrentIndex(1)
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_OVERVIEW)

        self.window().create_channel_button.clicked.connect(self.on_create_channel_button_pressed)
        self.window().edit_channel_save_button.clicked.connect(self.on_edit_channel_save_button_pressed)

        self.window().my_channel_torrents_remove_selected_button.clicked.connect(self.on_torrents_remove_selected_clicked)
        self.window().my_channel_torrents_remove_all_button.clicked.connect(self.on_torrents_remove_all_clicked)
        self.window().my_channel_torrents_add_button.clicked.connect(self.on_torrents_add_clicked)

        self.window().my_channel_details_playlist_manage.playlist_saved.connect(self.load_my_channel_playlists)

        self.window().edit_channel_playlist_torrents_back.clicked.connect(self.on_playlist_torrents_back_clicked)
        self.window().my_channel_playlists_list.itemClicked.connect(self.on_playlist_item_clicked)
        self.window().my_channel_playlist_manage_torrents_button.clicked.connect(self.on_playlist_manage_clicked)
        self.window().my_channel_create_playlist_button.clicked.connect(self.on_playlist_created_clicked)

        self.window().playlist_edit_save_button.clicked.connect(self.on_playlist_edit_save_clicked)
        self.window().playlist_edit_cancel_button.clicked.connect(self.on_playlist_edit_cancel_clicked)

        self.window().my_channel_details_rss_feeds_remove_selected_button.clicked.connect(self.on_rss_feeds_remove_selected_clicked)
        self.window().my_channel_details_rss_add_button.clicked.connect(self.on_rss_feed_add_clicked)
        self.window().my_channel_details_rss_refresh_button.clicked.connect(self.on_rss_feeds_refresh_clicked)

        # Tab bar buttons
        self.window().channel_settings_tab.initialize()
        self.window().channel_settings_tab.clicked_tab_button.connect(self.clicked_tab_button)

        self.remove_torrent_requests = []
        self.playlists = None
        self.editing_playlist = None
        self.viewing_playlist = None

        self.load_my_channel_overview()

    def load_my_channel_overview(self):
        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request("mychannel", self.initialize_with_overview)

    def initialize_with_overview(self, overview):
        if 'error' in overview:
            self.window().my_channel_stacked_widget.setCurrentIndex(0)
            self.window().my_channel_sharing_torrents.setHidden(True)
        else:
            self.my_channel_overview = overview
            self.window().my_channel_name_label.setText(overview["mychannel"]["name"])
            self.window().my_channel_description_label.setText(overview["mychannel"]["description"])
            self.window().my_channel_identifier_label.setText(overview["mychannel"]["identifier"])

            self.window().edit_channel_name_edit.setText(overview["mychannel"]["name"])
            self.window().edit_channel_description_edit.setText(overview["mychannel"]["description"])

            self.window().my_channel_stacked_widget.setCurrentIndex(1)

    def load_my_channel_torrents(self):
        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request("channels/discovered/%s/torrents" % self.my_channel_overview["mychannel"]["identifier"], self.initialize_with_torrents)

    def initialize_with_torrents(self, torrents):
        self.window().my_channel_torrents_list.set_data_items([])

        items = []
        for result in torrents['torrents']:
            items.append((ChannelTorrentListItem, result))
        self.window().my_channel_torrents_list.set_data_items(items)

    def load_my_channel_playlists(self):
        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request("channels/discovered/%s/playlists" % self.my_channel_overview["mychannel"]["identifier"], self.initialize_with_playlists)

    def initialize_with_playlists(self, playlists):
        self.playlists = playlists
        self.window().my_channel_playlists_list.set_data_items([])

        self.update_playlist_list()

        viewing_playlist_index = self.get_index_of_viewing_playlist()
        if viewing_playlist_index != -1:
            self.viewing_playlist = self.playlists['playlists'][viewing_playlist_index]
            self.update_playlist_torrent_list()

    def load_my_channel_rss_feeds(self):
        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request("channels/discovered/%s/rssfeeds" % self.my_channel_overview["mychannel"]["identifier"], self.initialize_with_rss_feeds)

    def initialize_with_rss_feeds(self, rss_feeds):
        self.window().my_channel_rss_feeds_list.clear()
        for feed in rss_feeds["rssfeeds"]:
            item = QTreeWidgetItem(self.window().my_channel_rss_feeds_list)
            item.setText(0, feed["url"])

            self.window().my_channel_rss_feeds_list.addTopLevelItem(item)

    def on_create_channel_button_pressed(self):
        channel_name = self.window().new_channel_name_edit.text()
        channel_description = self.window().new_channel_description_edit.toPlainText()
        if len(channel_name) == 0:
            self.window().new_channel_name_label.setStyleSheet("color: red;")
            return

        self.window().create_channel_button.setEnabled(False)
        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request("channels/discovered", self.on_channel_created, data=str('name=%s&description=%s' % (channel_name, channel_description)), method='PUT')

    def on_channel_created(self, result):
        if u'added' in result:
            self.window().create_channel_button.setEnabled(True)
            self.load_my_channel_overview()

    def on_edit_channel_save_button_pressed(self):
        channel_name = self.window().edit_channel_name_edit.text()
        channel_description = self.window().edit_channel_description_edit.toPlainText()
        self.window().edit_channel_save_button.setEnabled(False)

        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request("mychannel", self.on_channel_edited, data=str('name=%s&description=%s' % (channel_name, channel_description)), method='POST')

    def on_channel_edited(self, result):
        if 'edited' in result:
            self.window().my_channel_name_label.setText(self.window().edit_channel_name_edit.text())
            self.window().my_channel_description_label.setText(self.window().edit_channel_description_edit.toPlainText())
            self.window().edit_channel_save_button.setEnabled(True)

    def on_torrents_remove_selected_clicked(self):
        num_selected = len(self.window().my_channel_torrents_list.selectedItems())
        if num_selected == 0:
            return

        self.dialog = ConfirmationDialog(self, "Remove %s selected torrents" % num_selected,
                    "Are you sure that you want to remove %s selected torrents from your channel?" % num_selected, [('confirm', BUTTON_TYPE_NORMAL), ('cancel', BUTTON_TYPE_CONFIRM)])
        self.dialog.button_clicked.connect(self.on_torrents_remove_selected_action)
        self.dialog.show()

    def on_torrents_remove_all_clicked(self):
        self.dialog = ConfirmationDialog(self.window(), "Remove all torrents",
                    "Are you sure that you want to remove all torrents from your channel? You cannot undo this action.", [('confirm', BUTTON_TYPE_NORMAL), ('cancel', BUTTON_TYPE_CONFIRM)])
        self.dialog.button_clicked.connect(self.on_torrents_remove_all_action)
        self.dialog.show()

    def on_torrents_add_clicked(self):
        menu = TriblerActionMenu(self)

        browseFilesAction = QAction('Browse files', self)
        browseDirectoryAction = QAction('Browse directory', self)
        addUrlAction = QAction('Add URL', self)
        addFromLibraryAction = QAction('Add from library', self)
        createTorrentAction = QAction('Create torrent from file(s)', self)

        browseFilesAction.triggered.connect(self.on_add_torrent_browse_file)
        browseDirectoryAction.triggered.connect(self.on_add_torrent_browse_file)
        addUrlAction.triggered.connect(self.on_add_torrent_browse_file)
        addFromLibraryAction.triggered.connect(self.on_add_torrent_browse_file)
        createTorrentAction.triggered.connect(self.on_add_torrent_browse_file)

        menu.addAction(browseFilesAction)
        menu.addAction(browseDirectoryAction)
        menu.addAction(addUrlAction)
        menu.addAction(addFromLibraryAction)
        menu.addAction(createTorrentAction)

        menu.exec_(self.window().mapToGlobal(self.window().my_channel_torrents_add_button.pos()))

    def on_playlist_torrents_back_clicked(self):
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLISTS)

    def on_playlist_item_clicked(self, item):
        playlist_info = item.data(Qt.UserRole)
        self.window().my_channel_playlist_torrents_list.set_data_items([])
        self.window().my_channel_details_playlist_torrents_header.setText("Torrents in '%s'" % playlist_info['name'])

        self.viewing_playlist = playlist_info
        self.update_playlist_torrent_list()

        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLIST_TORRENTS)

    def update_playlist_list(self):
        self.playlists['playlists'].sort(key=lambda torrent: len(torrent['torrents']), reverse=True)

        items = []
        for result in self.playlists['playlists']:
            items.append((PlaylistListItem, result, {"show_controls": True, "on_remove_clicked": self.on_playlist_remove_clicked, "on_edit_clicked": self.on_playlist_edit_clicked}))
        self.window().my_channel_playlists_list.set_data_items(items)

    def update_playlist_torrent_list(self):
        items = []
        for torrent in self.viewing_playlist["torrents"]:
            items.append((ChannelTorrentListItem, torrent, {"show_controls": True, "on_remove_clicked": self.on_playlist_torrent_remove_clicked}))
        self.window().my_channel_playlist_torrents_list.set_data_items(items)

    def on_playlist_manage_clicked(self):
        self.window().my_channel_details_playlist_manage.initialize(self.my_channel_overview, self.viewing_playlist)
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLIST_MANAGE)

    def on_playlist_torrent_remove_clicked(self, item):
        self.dialog = ConfirmationDialog(self, "Remove selected torrent from playlist", "Are you sure that you want to remove the selected torrent from this playlist?", [('confirm', BUTTON_TYPE_NORMAL), ('cancel', BUTTON_TYPE_CONFIRM)])
        self.dialog.button_clicked.connect(lambda action: self.on_playlist_torrent_remove_selected_action(item, action))
        self.dialog.show()

    def on_playlist_torrent_remove_selected_action(self, item, action):
        if action == 0:
            self.mychannel_request_mgr = TriblerRequestManager()
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/playlists/%s/%s" % (self.my_channel_overview["mychannel"]["identifier"], self.viewing_playlist['id'], item.torrent_info['infohash']), lambda result: self.on_playlist_torrent_removed(result, item.torrent_info), method='DELETE')

        self.dialog.setParent(None)
        self.dialog = None

    def on_playlist_torrent_removed(self, result, torrent):
        self.remove_torrent_from_playlist(torrent)

    def get_index_of_viewing_playlist(self):
        if self.viewing_playlist is None:
            return -1

        for index in xrange(len(self.playlists['playlists'])):
            if self.playlists['playlists'][index]['id'] == self.viewing_playlist['id']:
                return index

        return -1

    def remove_torrent_from_playlist(self, torrent):
        playlist_index = self.get_index_of_viewing_playlist()

        torrent_index = -1
        for index in xrange(len(self.viewing_playlist['torrents'])):
            if self.viewing_playlist['torrents'][index]['infohash'] == torrent['infohash']:
                torrent_index = index
                break

        if torrent_index != -1:
            del self.playlists['playlists'][playlist_index]['torrents'][torrent_index]
            self.viewing_playlist = self.playlists['playlists'][playlist_index]
            self.update_playlist_list()
            self.update_playlist_torrent_list()

    def on_playlist_edit_save_clicked(self):
        if len(self.window().playlist_edit_name.text()) == 0:
            return

        name = self.window().playlist_edit_name.text()
        description = self.window().playlist_edit_description.toPlainText()

        self.mychannel_request_mgr = TriblerRequestManager()
        if self.editing_playlist is None:
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/playlists" % self.my_channel_overview["mychannel"]["identifier"], self.on_playlist_created, data=str('name=%s&description=%s' % (name, description)), method='PUT')
        else:
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/playlists/%s" % (self.my_channel_overview["mychannel"]["identifier"], self.editing_playlist["id"]), self.on_playlist_edited, data=str('name=%s&description=%s' % (name, description)), method='POST')

    def on_playlist_created(self, json_result):
        if 'created' in json_result and json_result['created']:
            self.on_playlist_edited_done()

    def on_playlist_edited(self, json_result):
        if 'modified' in json_result and json_result['modified']:
            self.on_playlist_edited_done()

    def on_playlist_edited_done(self):
        self.window().playlist_edit_name.setText('')
        self.window().playlist_edit_description.setText('')
        self.load_my_channel_playlists()
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLISTS)

    def on_playlist_edit_cancel_clicked(self):
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLISTS)

    def on_playlist_created_clicked(self):
        self.editing_playlist = None
        self.window().playlist_edit_save_button.setText("Create")
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLIST_EDIT)

    def on_playlist_remove_clicked(self, item):
        self.dialog = ConfirmationDialog(self, "Remove selected playlist", "Are you sure that you want to remove the selected playlist from your channel?", [('confirm', BUTTON_TYPE_NORMAL), ('cancel', BUTTON_TYPE_CONFIRM)])
        self.dialog.button_clicked.connect(lambda action: self.on_playlist_remove_selected_action(item, action))
        self.dialog.show()

    def on_playlist_remove_selected_action(self, item, action):
        if action == 0:
            self.mychannel_request_mgr = TriblerRequestManager()
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/playlists/%s" % (self.my_channel_overview["mychannel"]["identifier"], item.playlist_info['id']), self.on_playlist_removed, method='DELETE')

        self.dialog.setParent(None)
        self.dialog = None

    def on_playlist_removed(self, json_result):
        print json_result
        if 'removed' in json_result and json_result['removed']:
            self.load_my_channel_playlists()

    def on_playlist_edit_clicked(self, item):
        self.editing_playlist = item.playlist_info
        self.window().playlist_edit_save_button.setText("Create")
        self.window().playlist_edit_name.setText(item.playlist_info["name"])
        self.window().playlist_edit_description.setText(item.playlist_info["description"])
        self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLIST_EDIT)

    def on_add_torrent_browse_file(self):
        pass

    def on_torrents_remove_selected_action(self, action):
        if action == 0:
            torrent_data = self.window().my_channel_torrents_list.selectedItems()[0].data(Qt.UserRole)
            self.mychannel_request_mgr = TriblerRequestManager()
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/torrents/%s" % (self.my_channel_overview["mychannel"]["identifier"], torrent_data['infohash']), self.on_torrent_removed, method='DELETE')

        self.dialog.setParent(None)
        self.dialog = None

    def on_torrent_removed(self, json_result):
        if 'removed' in json_result and json_result['removed']:
            selected_item = self.window().my_channel_torrents_list.selectedItems()[0]
            self.window().my_channel_torrents_list.takeItem(self.window().my_channel_torrents_list.row(selected_item))

    def on_torrents_remove_all_action(self, action):
        if action == 0:
            for torrent_ind in xrange(self.window().my_channel_torrents_list.count()):
                torrent_data = self.window().my_channel_torrents_list.item(torrent_ind).data(Qt.UserRole)
                request_mgr = TriblerRequestManager()
                request_mgr.perform_request("channels/discovered/%s/torrents/%s" % (self.my_channel_overview["mychannel"]["identifier"], torrent_data['infohash']), None, method='DELETE')
                self.remove_torrent_requests.append(request_mgr)

            self.window().my_channel_torrents_list.set_data_items([])

        self.dialog.setParent(None)
        self.dialog = None

    def clicked_tab_button(self, tab_button_name):
        if tab_button_name == "my_channel_overview_button":
            self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_OVERVIEW)
        elif tab_button_name == "my_channel_settings_button":
            self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_SETTINGS)
        elif tab_button_name == "my_channel_torrents_button":
            self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_TORRENTS)
            self.load_my_channel_torrents()
        elif tab_button_name == "my_channel_playlists_button":
            self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_PLAYLISTS)
            self.load_my_channel_playlists()
        elif tab_button_name == "my_channel_rss_feeds_button":
            self.window().my_channel_details_stacked_widget.setCurrentIndex(PAGE_MY_CHANNEL_RSS_FEEDS)
            self.load_my_channel_rss_feeds()

    def on_create_channel_intro_button_clicked(self):
        self.window().create_channel_form.show()
        self.window().create_channel_intro_button_container.hide()
        self.window().create_new_channel_intro_label.setText("Please enter your channel details below.")

    def on_rss_feed_add_clicked(self):
        self.dialog = ConfirmationDialog(self, "Add RSS feed", "Please enter the RSS feed URL in the field below:", [('add', BUTTON_TYPE_NORMAL), ('cancel', BUTTON_TYPE_CONFIRM)], show_input=True)
        self.dialog.dialog_widget.dialog_input.setPlaceholderText('RSS feed URL')
        self.dialog.button_clicked.connect(self.on_rss_feed_dialog_added)
        self.dialog.show()

    def on_rss_feed_dialog_added(self, action):
        if action == 0:
            url = urllib.quote_plus(self.dialog.dialog_widget.dialog_input.text())
            self.mychannel_request_mgr = TriblerRequestManager()
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/rssfeeds/%s" % (self.my_channel_overview["mychannel"]["identifier"], url), self.on_rss_feed_added, method='PUT')

        self.dialog.setParent(None)
        self.dialog = None

    def on_rss_feed_added(self, json_result):
        if json_result['added']:
            self.load_my_channel_rss_feeds()

    def on_rss_feeds_remove_selected_clicked(self):
        self.dialog = ConfirmationDialog(self, "Remove RSS feed", "Are you sure you want to remove the selected RSS feed?", [('remove', BUTTON_TYPE_NORMAL), ('cancel', BUTTON_TYPE_CONFIRM)])
        self.dialog.button_clicked.connect(self.on_rss_feed_dialog_removed)
        self.dialog.show()

    def on_rss_feed_dialog_removed(self, action):
        if action == 0:
            url = urllib.quote_plus(self.window().my_channel_rss_feeds_list.selectedItems()[0].text(0))
            print url
            self.mychannel_request_mgr = TriblerRequestManager()
            self.mychannel_request_mgr.perform_request("channels/discovered/%s/rssfeeds/%s" % (self.my_channel_overview["mychannel"]["identifier"], url), self.on_rss_feed_removed, method='DELETE')

        self.dialog.setParent(None)
        self.dialog = None

    def on_rss_feed_removed(self, json_result):
        print json_result
        if json_result['removed']:
            self.load_my_channel_rss_feeds()

    def on_rss_feeds_refresh_clicked(self):
        self.window().my_channel_details_rss_refresh_button.setEnabled(False)
        self.mychannel_request_mgr = TriblerRequestManager()
        self.mychannel_request_mgr.perform_request('channels/discovered/%s/recheckfeeds' % self.my_channel_overview["mychannel"]["identifier"], self.on_rss_feeds_refreshed,  method='POST')

    def on_rss_feeds_refreshed(self, json_result):
        if json_result["rechecked"]:
            self.window().my_channel_details_rss_refresh_button.setEnabled(True)
