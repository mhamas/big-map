from typing import List, Tuple
from tqdm import tqdm

import os
import click
import imageio
import math
import numpy as np


EARTH_CIRCUMFERENCE_AT_EQUATOR_METERS = 40075016.686


def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """
    Shortest distance on a sphere
    https://en.wikipedia.org/wiki/Haversine_formula
    >>> import math
    >>> math.floor(haversine_distance(50, 14, 50, 14))
    0
    >>> math.floor(haversine_distance(50, 14, 51, 15))
    131780
    >>> math.floor(haversine_distance(50, 14, 70, 50))
    2906845
    """
    dlat_rad = np.radians(lat2) - np.radians(lat1)
    dlon_rad = np.radians(lon2) - np.radians(lon1)

    return (
        2
        * 6371
        * 1e3
        * np.arcsin(
            np.sqrt(
                np.sin(dlat_rad / 2) ** 2
                + np.cos(np.radians(lat1))
                * np.cos(np.radians(lat2))
                * np.sin(dlon_rad / 2) ** 2
            )
        )
    )


def deg2num(lat_deg, lon_deg, zoom):
    """From https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers_2
    Computes tile indices given GPS coordinates and zoom level
    """
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def num2deg(xtile, ytile, zoom):
    """From https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers_2
    Returns coordinates of NW corner of the tile
    """
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)


def compute_zoom_level(lat: float, lon1: float, lon2: float, width_px: int):
    num_tiles = math.ceil(width_px / 256)  # each tile is 256x256px, dictated by mapbox

    # Horizontal distance in meters between lon1 and lon2 @ lat
    horizontal_distance_meters = haversine_distance(
        lat1=lat, lon1=lon1, lat2=lat, lon2=lon2
    )
    horizontal_distance_tile_meters = horizontal_distance_meters / num_tiles

    # horizontal_distance_tile_meters is  EARTH_CIRCUMFERENCE_AT_EQUATOR_METERS * math.cos(lat) * (2 ** zoom)
    # as per https://wiki.openstreetmap.org/wiki/Zoom_levels
    return math.ceil(
        math.log2(
            (EARTH_CIRCUMFERENCE_AT_EQUATOR_METERS * math.cos(np.radians(lat)))
            / horizontal_distance_tile_meters
        )
    )


def get_url_of_static_raster_file(
    lat_min_deg: float,
    lat_max_deg: float,
    lon_min_deg: float,
    lon_max_deg: float,
    token: str,
    style_id: str,
    high_resolution: bool,
):
    h = "@2x" if high_resolution else ""
    return f"https://api.mapbox.com/styles/v1/mapbox/{style_id}/static/[{lon_min_deg},{lat_min_deg},{lon_max_deg},{lat_max_deg}]/256x256{h}?access_token={token}&logo=false&attribution=false"


@click.command("Create tiled map")
@click.option(
    "--lat-min-deg",
    required=True,
    type=float,
    help="Minimum latitude in degrees",
)
@click.option(
    "--lat-max-deg",
    required=True,
    type=float,
    help="Maximum latitude in degrees",
)
@click.option(
    "--lon-min-deg",
    required=True,
    type=float,
    help="Minimum longitude in degrees",
)
@click.option(
    "--lon-max-deg",
    required=True,
    type=float,
    help="Maximum longitude in degrees",
)
@click.option(
    "--width-px",
    required=True,
    type=int,
    help="Width of the resulting image in pixels",
)
@click.option(
    "-o",
    "--output-dir",
    required=True,
    type=str,
    help="Where the output will be stored",
)
@click.option(
    "--mapbox-style-id",
    type=str,
    default="streets-v11",
    help="Mapbox style id (https://docs.mapbox.com/api/maps/styles/)",
)
@click.option(
    "--mapbox-token",
    required=True,
    type=str,
    help="Token for mapbox API used to query the tiles",
)
@click.option(
    "--high-resolution",
    is_flag=True,
    help="Render at 2x resolution",
)
def create_map(
    lat_min_deg: float,
    lat_max_deg: float,
    lon_min_deg: float,
    lon_max_deg: float,
    width_px: int,
    output_dir: str,
    mapbox_style_id: str,
    mapbox_token: str,
    high_resolution: bool,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    zoom = compute_zoom_level(
        lat=lat_min_deg,
        lon1=lon_min_deg,
        lon2=lon_max_deg,
        width_px=width_px,
    )

    # Tile indices of the extreme tiles
    x1, y1 = deg2num(lat_deg=lat_min_deg, lon_deg=lon_min_deg, zoom=zoom)
    x2, y2 = deg2num(lat_deg=lat_max_deg, lon_deg=lon_max_deg, zoom=zoom)

    # This could happen if lat, lon is swapped on input
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    num_tiles_x = x2 - x1 + 1
    num_tiles_y = y2 - y1 + 1
    num_tiles = num_tiles_x * num_tiles_y
    tile_size = 512 if high_resolution else 256  # this is dictated by mapbox

    stitched_image = np.zeros((tile_size * num_tiles_y, tile_size * num_tiles_x, 3))

    print(f"Querying for {num_tiles} tiles")
    with tqdm(total=num_tiles) as pbar:
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                # nw - north west
                lat_nw, lon_nw = num2deg(xtile=x, ytile=y, zoom=zoom)
                # se - south east
                lat_se, lon_se = num2deg(xtile=x + 1, ytile=y + 1, zoom=zoom)

                url = get_url_of_static_raster_file(
                    lat_min_deg=min(lat_nw, lat_se),
                    lat_max_deg=max(lat_nw, lat_se),
                    lon_min_deg=min(lon_nw, lon_se),
                    lon_max_deg=max(lon_nw, lon_se),
                    token=mapbox_token,
                    style_id=mapbox_style_id,
                    high_resolution=high_resolution,
                )

                img = imageio.imread(url)[:, :, :3]
                stitched_image[
                    (y - y1) * tile_size : (y - y1 + 1) * tile_size,
                    (x - x1) * tile_size : (x - x1 + 1) * tile_size,
                    :,
                ] = img

                imageio.imwrite(os.path.join(output_dir, f"{x}_{y}_{zoom}.jpg"), img)

                pbar.update(1)
    imageio.imwrite(os.path.join(output_dir, "result.jpg"), stitched_image)

    print("Success 🎉")


if __name__ == "__main__":
    create_map()
