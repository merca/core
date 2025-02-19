"""Media browsing tests for the forked_daapd media player platform."""

from http import HTTPStatus
from unittest.mock import patch

from homeassistant.components import media_source
from homeassistant.components.forked_daapd.browse_media import create_media_content_id
from homeassistant.components.media_player import MediaType
from homeassistant.components.websocket_api.const import TYPE_RESULT
from homeassistant.setup import async_setup_component

TEST_MASTER_ENTITY_NAME = "media_player.forked_daapd_server"


async def test_async_browse_media(hass, hass_ws_client, config_entry):
    """Test browse media."""

    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.forked_daapd.media_player.ForkedDaapdAPI",
        autospec=True,
    ) as mock_api:
        config_entry.add_to_hass(hass)
        await config_entry.async_setup(hass)
        await hass.async_block_till_done()

        mock_api.return_value.full_url = lambda x: "http://owntone_instance/" + x
        mock_api.return_value.get_directory.side_effect = [
            {
                "directories": [
                    {"path": "/music/srv/Audiobooks"},
                    {"path": "/music/srv/Music"},
                    {"path": "/music/srv/Playlists"},
                    {"path": "/music/srv/Podcasts"},
                ],
                "tracks": {
                    "items": [
                        {
                            "id": 1,
                            "title": "input.pipe",
                            "artist": "Unknown artist",
                            "artist_sort": "Unknown artist",
                            "album": "Unknown album",
                            "album_sort": "Unknown album",
                            "album_id": "4201163758598356043",
                            "album_artist": "Unknown artist",
                            "album_artist_sort": "Unknown artist",
                            "album_artist_id": "4187901437947843388",
                            "genre": "Unknown genre",
                            "year": 0,
                            "track_number": 0,
                            "disc_number": 0,
                            "length_ms": 0,
                            "play_count": 0,
                            "skip_count": 0,
                            "time_added": "2018-11-24T08:41:35Z",
                            "seek_ms": 0,
                            "media_kind": "music",
                            "data_kind": "pipe",
                            "path": "/music/srv/input.pipe",
                            "uri": "library:track:1",
                            "artwork_url": "/artwork/item/1",
                        }
                    ],
                    "total": 1,
                    "offset": 0,
                    "limit": -1,
                },
                "playlists": {
                    "items": [
                        {
                            "id": 8,
                            "name": "radio",
                            "path": "/music/srv/radio.m3u",
                            "smart_playlist": True,
                            "uri": "library:playlist:8",
                        }
                    ],
                    "total": 1,
                    "offset": 0,
                    "limit": -1,
                },
            }
        ] + 4 * [
            {"directories": [], "tracks": {"items": []}, "playlists": {"items": []}}
        ]
        mock_api.return_value.get_albums.return_value = [
            {
                "id": "8009851123233197743",
                "name": "Add Violence",
                "name_sort": "Add Violence",
                "artist": "Nine Inch Nails",
                "artist_id": "32561671101664759",
                "track_count": 5,
                "length_ms": 1634961,
                "uri": "library:album:8009851123233197743",
            },
        ]
        mock_api.return_value.get_artists.return_value = [
            {
                "id": "3815427709949443149",
                "name": "ABAY",
                "name_sort": "ABAY",
                "album_count": 1,
                "track_count": 10,
                "length_ms": 2951554,
                "uri": "library:artist:3815427709949443149",
            },
        ]
        mock_api.return_value.get_genres.return_value = [
            {"name": "Classical"},
            {"name": "Drum & Bass"},
            {"name": "Pop"},
            {"name": "Rock/Pop"},
            {"name": "'90s Alternative"},
        ]
        mock_api.return_value.get_playlists.return_value = [
            {
                "id": 1,
                "name": "radio",
                "path": "/music/srv/radio.m3u",
                "smart_playlist": False,
                "uri": "library:playlist:1",
            },
        ]

        # Request playlist through WebSocket
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "media_player/browse_media",
                "entity_id": TEST_MASTER_ENTITY_NAME,
            }
        )
        msg = await client.receive_json()
        # Assert WebSocket response
        assert msg["id"] == 1
        assert msg["type"] == TYPE_RESULT
        assert msg["success"]

        msg_id = 2

        async def browse_children(children):
            """Browse the children of this BrowseMedia."""
            nonlocal msg_id
            for child in children:
                if child["can_expand"]:
                    print("EXPANDING CHILD", child)
                    await client.send_json(
                        {
                            "id": msg_id,
                            "type": "media_player/browse_media",
                            "entity_id": TEST_MASTER_ENTITY_NAME,
                            "media_content_type": child["media_content_type"],
                            "media_content_id": child["media_content_id"],
                        }
                    )
                    msg = await client.receive_json()
                    assert msg["success"]
                    msg_id += 1
                    await browse_children(msg["result"]["children"])

        await browse_children(msg["result"]["children"])


async def test_async_browse_media_not_found(hass, hass_ws_client, config_entry):
    """Test browse media not found."""

    assert await async_setup_component(hass, media_source.DOMAIN, {})
    await hass.async_block_till_done()

    with patch(
        "homeassistant.components.forked_daapd.media_player.ForkedDaapdAPI",
        autospec=True,
    ) as mock_api:
        config_entry.add_to_hass(hass)
        await config_entry.async_setup(hass)
        await hass.async_block_till_done()

        mock_api.return_value.get_directory.return_value = None
        mock_api.return_value.get_albums.return_value = None
        mock_api.return_value.get_artists.return_value = None
        mock_api.return_value.get_genres.return_value = None
        mock_api.return_value.get_playlists.return_value = None

        # Request playlist through WebSocket
        client = await hass_ws_client(hass)
        msg_id = 1
        for media_type in (
            "directory",
            MediaType.ALBUM,
            MediaType.ARTIST,
            MediaType.GENRE,
            MediaType.PLAYLIST,
        ):
            await client.send_json(
                {
                    "id": msg_id,
                    "type": "media_player/browse_media",
                    "entity_id": TEST_MASTER_ENTITY_NAME,
                    "media_content_type": media_type,
                    "media_content_id": (
                        media_content_id := create_media_content_id(
                            "title", f"library:{media_type}:"
                        )
                    ),
                }
            )
            msg = await client.receive_json()
            # Assert WebSocket response
            assert msg["id"] == msg_id
            assert msg["type"] == TYPE_RESULT
            assert not msg["success"]
            assert (
                msg["error"]["message"]
                == f"Media not found for {media_type} / {media_content_id}"
            )
            msg_id += 1


async def test_async_browse_image(hass, hass_client, config_entry):
    """Test browse media images."""

    with patch(
        "homeassistant.components.forked_daapd.media_player.ForkedDaapdAPI",
        autospec=True,
    ) as mock_api:
        config_entry.add_to_hass(hass)
        await config_entry.async_setup(hass)
        await hass.async_block_till_done()
        client = await hass_client()
        mock_api.return_value.full_url = lambda x: "http://owntone_instance/" + x
        mock_api.return_value.get_albums.return_value = [
            {"id": "8009851123233197743", "artwork_url": "some_album_image"},
        ]
        mock_api.return_value.get_artists.return_value = [
            {"id": "3815427709949443149", "artwork_url": "some_artist_image"},
        ]
        mock_api.return_value.get_track.return_value = {
            "id": 456,
            "artwork_url": "some_track_image",
        }
        media_content_id = create_media_content_id(
            "title", media_type=MediaType.ALBUM, id_or_path="8009851123233197743"
        )

        with patch(
            "homeassistant.components.media_player.async_fetch_image"
        ) as mock_fetch_image:
            for media_type, media_id in (
                (MediaType.ALBUM, "8009851123233197743"),
                (MediaType.ARTIST, "3815427709949443149"),
                (MediaType.TRACK, "456"),
            ):
                mock_fetch_image.return_value = (b"image_bytes", media_type)
                media_content_id = create_media_content_id(
                    "title", media_type=media_type, id_or_path=media_id
                )
                resp = await client.get(
                    f"/api/media_player_proxy/{TEST_MASTER_ENTITY_NAME}/browse_media/{media_type}/{media_content_id}"
                )
                assert (
                    mock_fetch_image.call_args[0][2]
                    == f"http://owntone_instance/some_{media_type}_image"
                )
                assert resp.status == HTTPStatus.OK
                assert resp.content_type == media_type
                assert await resp.read() == b"image_bytes"


async def test_async_browse_image_missing(hass, hass_client, config_entry, caplog):
    """Test browse media images with no image available."""

    with patch(
        "homeassistant.components.forked_daapd.media_player.ForkedDaapdAPI",
        autospec=True,
    ) as mock_api:
        config_entry.add_to_hass(hass)
        await config_entry.async_setup(hass)
        await hass.async_block_till_done()
        client = await hass_client()
        mock_api.return_value.full_url = lambda x: "http://owntone_instance/" + x
        mock_api.return_value.get_track.return_value = {}

        media_content_id = create_media_content_id(
            "title", media_type=MediaType.TRACK, id_or_path="456"
        )
        resp = await client.get(
            f"/api/media_player_proxy/{TEST_MASTER_ENTITY_NAME}/browse_media/{MediaType.TRACK}/{media_content_id}"
        )
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR
