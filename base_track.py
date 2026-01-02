import folium
import pandas as pd
import plotly.graph_objects as go
import webbrowser
from geopy.distance import geodesic
from datetime import timedelta
from pathlib import Path


class BaseTrack:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    @property
    def total_time(self) -> timedelta:
        """
        Calculate activity total time
        :return: total time of activity [timedelta]
        """
        start = self.df['time'].iloc[0]
        end = self.df['time'].iloc[-1]
        seconds = (end - start).total_seconds()
        return timedelta(seconds=int(seconds))

    @property
    def distance(self) -> float:
        """
        Calculate total distance of activity
        :return: total distance of activity [km]
        """
        distance = 0.0
        for i in range(1, len(self.df)):
            p1 = (self.df.iloc[i - 1]['lat'], self.df.iloc[i - 1]['lon'])
            p2 = (self.df.iloc[i]['lat'], self.df.iloc[i]['lon'])
            distance += geodesic(p1, p2).meters
        return round(distance / 1000, 2)

    @property
    def total_ascent(self) -> int:
        """
        Calculate total ascent during activity
        :return: total ascent [m]
        """
        threshold = 0.088     # [m]
        ele_smooth = self.df['ele'].rolling(
            window=5,
            center=True,
            min_periods=1
        ).mean()

        diff = ele_smooth.diff()
        ascent = diff[diff > threshold].sum()

        return int(ascent)

    @property
    def moving_time(self) -> timedelta:
        """
        Calculate moving time = total time - pause time
        :return: moving time during activity [timedelta]
        """
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

    def generate_elevation_profile(self) -> str:
        """
        Generate elevation profile
        :return: figure with elevation profile
        """
        df = self.df.copy()
        distances = [0.0]

        for i in range(1, len(df)):
            p1 = (df.iloc[i - 1]['lat'], df.iloc[i - 1]['lon'])
            p2 = (df.iloc[i]['lat'], df.iloc[i]['lon'])
            distances.append(distances[-1] + geodesic(p1, p2).meters / 1000)

        df['dist_km'] = distances

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['dist_km'],
            y=df['ele'],
            mode='lines',
            fill='tozeroy',
            name='Elevation'
        ))

        fig.update_layout(
            autosize=True,
            height=250,
            margin=dict(l=20, r=20, t=30, b=30),
            showlegend=False
        )
        return fig.to_html(include_plotlyjs='cdn', full_html=False)

    def stats_html(self) -> str:
        """
        Prepare html code with basic statistics
        :return: basic statistics in html code
        """
        return f"""
        <ul>
            <li><b>Distance:</b> {self.distance} km</li>
            <li><b>Total time:</b> {self.total_time}</li>
            <li><b>Moving time:</b> {self.moving_time}</li>
            <li><b>Elevation:</b> {self.total_ascent} m</li>
        </ul>
        """

    def show_map(self, color: str = 'blue',
                 output_file: str = 'prepared_maps/map.html',
                 open_browser: bool = True) -> str:
        """
        Generate html file with map of activity, basic statistics and elevation profile
        :param color: color of track on the map and describe writings
        :param output_file: path to file, where map will be saved
        :param open_browser: if True, map will be automatically open in browser
        :return: path to saved file with map
        """
        df = self.df.iloc[::5]
        start = df.iloc[0]

        m = folium.Map(location=[start['lat'], start['lon']],
                       zoom_start=10,
                       tiles='OpenStreetMap')

        points = list(zip(df['lat'], df['lon']))
        folium.PolyLine(points, color=color, weigh=4, opacity=0.8).add_to(m)

        folium.Marker(points[0], tooltip='Start').add_to(m)
        folium.Marker(points[-1], tooltip='Finish').add_to(m)

        html = f"""
            <div style="position: fixed;
                        bottom: 0;
                        left: 0;
                        width: 100%;
                        max-width: 100%,
                        background: white;
                        padding: 10px;
                        z-index: 9999;
                        border-radius: 8px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.4);
                        color: {color}">
                {self.stats_html()}
                {self.generate_elevation_profile()}
            </div>
            """

        m.get_root().html.add_child(folium.Element(html))
        m.save(output_file)

        if open_browser:
            path = Path(output_file).resolve()
            webbrowser.open(path.as_uri())

        return output_file
