import folium
import gpxpy
import matplotlib.pyplot as plt
import pandas as pd
from geopy.distance import geodesic
from datetime import timedelta
from pathlib import Path


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

    def save_elevation_profile(self, output_file='elevation.png'):
        df = self.df.copy()
        distances = [0.0]

        for i in range(1, len(df)):
            p1 = (df.iloc[i - 1]['lat'], df.iloc[i - 1]['lon'])
            p2 = (df.iloc[i]['lat'], df.iloc[i]['lon'])
            distances.append(distances[-1] + geodesic(p1, p2).meters / 1000)

        df['dist_km'] = distances

        plt.rcParams.update({'font.size': 25})
        plt.figure(figsize=(20, 4))
        plt.plot(df['dist_km'], df['ele'], linewidth=1)
        plt.fill_between(df['dist_km'], df['ele'], alpha=0.3)

        plt.xlabel('Distance [km]')
        plt.ylabel('Elevation [m]')
        plt.tight_layout()

        plt.savefig(output_file, dpi=150)
        plt.close()

        return Path(output_file)

    def stats_html(self):
        return f"""
        <ul>
            <li><b>Dystans:</b> {self.distance / 1000:.2f} km</li>
            <li><b>Czas całkowity:</b> {self.total_time}</li>
            <li><b>Czas jazdy:</b> {self.moving_time}</li>
        </ul>
        """

    def show_map(self, color='red', output_file='map.html'):
        start = self.df.iloc[0]

        m = folium.Map(location=[start['lat'], start['lon']],
                       zoom_start=13,
                       tiles='OpenStreetMap')

        points = list(zip(self.df['lat'], self.df['lon']))
        folium.PolyLine(points, color=color, weigh=4, opacity=0.8).add_to(m)

        folium.Marker(points[0], tooltip='Start').add_to(m)
        folium.Marker(points[-1], tooltip='Finish').add_to(m)

        elevation_img = self.save_elevation_profile()

        html = f"""
            <div style="position: fixed;
                        bottom: 10px;
                        left: 10px;
                        width: 800px;
                        background: white;
                        padding: 10px;
                        z-index: 9999;
                        border-radius: 8px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.3);">
                {self.stats_html()}
                <img src="{elevation_img.name}" width="100%">
            </div>
            """

        m.get_root().html.add_child(folium.Element(html))
        m.save(output_file)
        return output_file


file = 'test.gpx'
track = GpxTrack(file)
print(f'czas: {track.total_time}')
print(f'czas jazdy: {track.moving_time}')
print(f'dystans: {track.distance} km')
track.show_map(color='blue')
