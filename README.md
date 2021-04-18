# Big map

This tool helps you to create a big static raster map using individual
static raster tiles from mapbox that will be stitched together. You will need to use your own mapbox token. The output is indiviual tiles and and a single stitched image.

## Usage

Clone this repo and run `python -m main.py`. You will need to have the following dependencies installed in your environment.
- tqdm
- click
- imageio
- numpy

## Input
```
python main.py --help
Usage: main.py [OPTIONS]

Options:
  --lat-min-deg FLOAT     Minimum latitude in degrees  [required]
  --lat-max-deg FLOAT     Maximum latitude in degrees  [required]
  --lon-min-deg FLOAT     Minimum longitude in degrees  [required]
  --lon-max-deg FLOAT     Maximum longitude in degrees  [required]
  --width-px INTEGER      Width of the resulting image in pixels  [required]
  -o, --output-dir TEXT   Where the output will be stored  [required]
  --mapbox-style-id TEXT  Mapbox style id
                          (https://docs.mapbox.com/api/maps/styles/)

  --mapbox-token TEXT     Token for mapbox API used to query the tiles
                          [required]

  --high-resolution       Render at 2x resolution
  --help                  Show this message and exit.
```
### Output
Output dir given by `--output-dir` argument will be created if it doesn't exist.
It will contain files `x_y_zoom.jpg` for each downloaded tile and special file `result.jpg` with all tiles stiched together. Each tile is of size `256x256px`. If you specify `--high-resolution`, each tile will have size `512x512px`

## Example
This example downloads and stitches a map of SF.
```
python main.py \
--lat-min-deg 37.71799332543959 \
--lat-max-deg 37.816536359019565 \
--lon-min-deg -122.54354774871872 \
--lon-max-deg -122.35315469914812 \
--width-px 1000 \
--output-dir sf_map \
--mapbox-token {YOUR_MAPBOX_TOKEN} \
--high-resolution
```
