[general]
family_filter = boolean(default=True)
state_dir = string(default=None)
install_dir = string(default=.)
eckeypairfilename = string(default=None)
megacache = boolean(default=True)
videoanalyserpath = string(default=None)

[allchannel_community]
enabled = boolean(default=True)

[channel_community]
enabled = boolean(default=True)

[preview_channel_community]
enabled = boolean(default=True)

[search_community]
enabled = boolean(default=True)

[tunnel_community]
socks5_listen_ports = string_list(default=list('-1', '-1', '-1', '-1', '-1'))
exitnode_enabled = boolean(default=False)
enabled = boolean(default=True)

[multichain]
enabled = boolean(default=True)

[barter_community]
enabled = boolean(default=False)

[metadata]
enabled = boolean(default=True)
store_dir = string(default=None)

[mainline_dht]
enabled = boolean(default=True)
port = integer(min=-1, max=65536, default=-1)

[torrent_checking]
enabled = boolean(default=True)

[torrent_store]
enabled = boolean(default=True)
store_dir = string(default=None)

[torrent_collecting]
enabled = boolean(default=True)
dht_torrent_collecting = boolean(default=True)
torrent_collecting_max_torrents = integer(default=50000)
torrent_collecting_dir = string(default=None)
stop_collecting_threshold = integer(default=200)

[libtorrent]
enabled = boolean(default=True)
port = integer(min=1, max=65536)
lt_proxytype = integer(min=0, max=5, default=0)
lt_proxyserver = string(default=None)
lt_proxyauth = string(default=None)
utp = boolean(default=True)

# Anon settings
anon_listen_port = integer(min=-1, max=65536, default=-1)
anon_proxytype = integer(min=0, max=5, default=0)
anon_proxyserver = string(default=None)
anon_proxyauth = string(default=None)

[dispersy]
enabled = boolean(default=True)
port = integer(min=1, max=65536, default=7759)

[video_server]
enabled = boolean(default=True)
port = integer(min=-1, max=65536, default=-1)

[upgrader]
enabled = boolean(default=True)

[watch_folder]
enabled = boolean(default=True)
watch_folder_dir = string(default=None)

[http_api]
enabled = boolean(default=True)
port = integer(min=-1, max=65536, default=-1)

[credit_mining]
enabled = boolean(default=False)
max_torrents_per_source = integer(default=20)
max_torrents_active = integer(default=50)
source_interval = integer(default=100)
swarm_interval = integer(default=100)
share_mode_target = integer(default=3)
tracker_interval = integer(default=200)
logging_interval = integer(default=60)
# By default we want to automatically boost legal-predetermined channels
boosting_sources = string_list(default=list('http://bt.etree.org/rss/bt_etree_org.rdf'))
boosting_enabled = string_list(default=list('http://bt.etree.org/rss/bt_etree_org.rdf'))
boosting_disabled = string_list(default=list())
archive_sources = string_list(default=list())
policy = string(default=seederratio)

[user_download_states]
