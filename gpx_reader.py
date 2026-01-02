import gpxpy
import pandas as pd
from base_track import BaseTrack


class GpxTrack(BaseTrack):
    """
    Class for separate gpx track
    """
    def __init__(self, gpx_file: str):
        df = self._load_gpx(gpx_file)
        super().__init__(df)

    def _load_gpx(self, gpx_file: str) -> pd.DataFrame:
        """
        Load gpx file and save data into data frame with columns:
        lat - latitude
        lon - longitude
        ele - elevation
        time - time per point
        :param gpx_file: path to gpx file
        :return: pd.DataFrame with data from gpx file
        """
        rows = []
        with open(gpx_file, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)

        for track in gpx.tracks:
            for segment in track.segments:
                for p in segment.points:
                    rows.append({
                        'lat': p.latitude,
                        'lon': p.longitude,
                        'ele': p.elevation,
                        'time': p.time
                    })

        df = pd.DataFrame(rows)
        df = df.dropna(subset=['lat', 'lon'])
        return df


class GxpRoute(BaseTrack):
    """
    Class for combined gpx tracks - ready route
    """
    def __init__(self, gpx_files):
        dfs = [GpxTrack(f).df for f in gpx_files]
        df = pd.concat(dfs, ignore_index=True)
        df = df.sort_values('time').reset_index(drop=True)
        super().__init__(df)


route = GxpRoute([
    "tracks/day_1.gpx",
    "tracks/day_2_1.gpx",
    "tracks/day_2_2.gpx",
    "tracks/day_3.gpx"
])
route.show_map()
