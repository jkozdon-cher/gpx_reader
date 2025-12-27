import folium
import gpxpy
import pandas as pd
from geopy.distance import geodesic
from datetime import timedelta


class GpxTrack:
    def __init__(self, gpx_file: str):
        self.gpx_file = gpx_file
        self.df = self._load_gpx()

    def _load_gpx(self) -> pd.DataFrame:
        rows = []
        with open(self.gpx_file, 'r', encoding='utf-8') as f:
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

    @property
    def total_time(self):
        start = self.df['time'].iloc[0]
        end = self.df['time'].iloc[-1]
        seconds = (end - start).total_seconds()
        return timedelta(seconds=int(seconds))

    @property
    def distance(self) -> float:
        distance = 0.0
        for i in range(1, len(self.df)):
            p1 = (self.df.iloc[i - 1]['lat'], self.df.iloc[i - 1]['lon'])
            p2 = (self.df.iloc[i]['lat'], self.df.iloc[i]['lon'])
            distance += geodesic(p1, p2).meters
        return round(distance / 1000, 2)

    @property
    def moving_time(self):
        min_speed_kmh = 0.5
        min_distance_m = 1.0
        stop_tolerance_s = 5.0

        moving_seconds = 0.0
        stopped_seconds = 0.0
        for i in range(1, len(self.df)):
            p1 = self.df.iloc[i - 1]
            p2 = self.df.iloc[i]

            if p1['time'] is None or p2['time'] is None:
                continue

            dt = (p2['time'] - p1['time']).total_seconds()
            if dt <= 0:
                continue

            dist = geodesic((p1['lat'], p1['lon']),
                            (p2['lat'], p2['lon'])
                            ).meters
            speed_kmh = (dist / dt) * 3.6 if dt > 0 else 0

            if dist >= min_distance_m and speed_kmh >= min_speed_kmh:
                moving_seconds += dt
                stopped_seconds = 0
            else:
                stopped_seconds += dt
                if stopped_seconds <= stop_tolerance_s:
                    moving_seconds += dt

        return timedelta(seconds=int(moving_seconds))

    def show_map(self, color='red', output_file='map.html'):
        start_lat = self.df.iloc[0]['lat']
        start_lon = self.df.iloc[0]['lon']

        m = folium.Map(location=[start_lat, start_lon],
                       zoom_start=13,
                       tiles='OpenStreetMap')

        points = list(zip(self.df['lat'], self.df['lon']))
        folium.PolyLine(points, color=color, weigh=4, opacity=0.8).add_to(m)

        folium.Marker(points[0], tooltip='Start').add_to(m)
        folium.Marker(points[-1], tooltip='Finish').add_to(m)

        m.save(output_file)
        return output_file


file = 'test.gpx'
track = GpxTrack(file)
print(f'czas: {track.total_time}')
print(f'czas jazdy: {track.moving_time}')
print(f'dystans: {track.distance} km')
track.show_map(color='blue')
