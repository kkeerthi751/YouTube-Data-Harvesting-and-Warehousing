import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import seaborn as sns
import pymongo
from pymongo import MongoClient
from datetime import datetime
import re
import mysql.connector
from datetime import timedelta
import mysql.connector as mysql
import mysql.connector

Api_key = 'AIzaSyA_1jfxgQWmw1H_-6wOPzjG0ZnAEpSfdVg'

st.set_page_config(layout="wide")

st.title("Youtube Data Harvesting")

youtube = build('youtube', 'v3', developerKey=Api_key)

channel_ids = st.text_input("Enter Channnel Id")


def Get_Channel_details(youtube, channel_ids):
    channel_list = []
    request = youtube.channels().list(part='snippet,contentDetails,statistics', id=channel_ids)
    response = request.execute()
    for i in range(len(response["items"])):
        data = dict(channel_name=response["items"][i]["snippet"]["title"],
                    channel_id=response["items"][i]["id"],
                    subscription_count=response["items"][i]['statistics']['subscriberCount'],
                    channel_views=response["items"][i]['statistics']['viewCount'],
                    channel_description=response["items"][i]["snippet"]["description"],
                    playlist_id=response["items"][i]['contentDetails']['relatedPlaylists']['uploads'],
                    video_count=response["items"][i]["statistics"]["videoCount"])
        channel_list.append(data)
    return channel_list


# st.write(channels_data)


def play_list_(channel_ids):
    all_data = []
    request = youtube.playlists().list(part="snippet,id", channelId=channel_ids, maxResults=10)
    response = request.execute()
    for k in range(len(response["items"])):
        data = dict(playlist_id=response["items"][k]["id"],
                    channel_id=response["items"][k]["snippet"]["channelId"],
                    playlist_name=response["items"][k]["snippet"]["title"])
        all_data.append(data)
    return all_data


def playlist_id(channel_data):
    playlist_id = []
    for i in channel_data:
        playlist_id.append(i["playlist_id"])
    return playlist_id


def Get_video_details(youtube, playlist_ids):
    video_id = []
    for i in playlist_ids:
        request = youtube.playlistItems().list(part="snippet,contentDetails", playlistId=i, maxResults=10)
        response = request.execute()
        for j in range(len(response["items"])):
            video_id.append(response["items"][j]["contentDetails"]["videoId"])
    return video_id


def Get_video_data(youtube, playlist_ids, video_ids):
    all_data = []
    for k in playlist_ids:
        for i in video_ids:
            request = youtube.videos().list(part="snippet,statistics,contentDetails", id=i, maxResults=10)
            response = request.execute()
            for j in range(len(response["items"])):
                duration = response["items"][j]['contentDetails']['duration']

            # Extract hours, minutes, and seconds using regular expressions
            matches = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
            hours = int(matches.group(1)[:-1]) if matches.group(1) else 0
            minutes = int(matches.group(2)[:-1]) if matches.group(2) else 0
            seconds = int(matches.group(3)[:-1]) if matches.group(3) else 0
            # Calculate the total duration in seconds
            total_seconds = hours * 3600 + minutes * 60 + seconds

            # Create a timedelta object for the duration
            duration_obj = timedelta(seconds=total_seconds)

            # Convert the duration object to a formatted string
            new_duration = str(duration_obj)
            data = dict(playlist_id=k,
                        video_id=response["items"][j]["id"],
                        video_name=response["items"][j]["snippet"]["title"],
                        video_description=response["items"][j]["snippet"]["description"],
                        published_At=response["items"][j]["snippet"]["publishedAt"],
                        # Tags=response["items"][j]["snippet"]["tags"],
                        view_count=response["items"][j]["statistics"]["viewCount"],
                        like_count=response["items"][j]["statistics"]["likeCount"],
                        favorite_count=response["items"][j]["statistics"]["favoriteCount"],
                        duration=new_duration,
                        Thumnails=response["items"][j]["snippet"]["thumbnails"]["default"]["url"],
                        comment_count=response["items"][j]["statistics"]["commentCount"],
                        caption_status=response["items"][j]["contentDetails"]["caption"])
            all_data.append(data)
    return all_data


def comment_data(video_ids):
    all_data = []
    for i in video_ids:
        request = youtube.commentThreads().list(part="id,snippet,replies", videoId=i, maxResults=2)
        response = request.execute()
        for k in range(len(response["items"])):
            data = dict(comment_id=response["items"][k]["snippet"]["topLevelComment"]["id"],
                        comment_text=response["items"][k]["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                        comment_author=response["items"][k]["snippet"]["topLevelComment"]["snippet"][
                            "authorDisplayName"],
                        comment_publishedAt=response["items"][k]["snippet"]["topLevelComment"]["snippet"][
                            "publishedAt"])
            all_data.append(data)
    return all_data


if channel_ids:
    channel_data = Get_Channel_details(youtube, channel_ids)
    channels_data = pd.DataFrame(channel_data)
    playlist_ids = playlist_id(channel_data)
    playlist_details = play_list_(channel_ids)
    playlists_details = pd.DataFrame(playlist_details)
    video_ids = Get_video_details(youtube, playlist_ids)
    video_details = Get_video_data(youtube, playlist_ids, video_ids)
    videos_details = pd.DataFrame(video_details)
    comment_details = comment_data(video_ids)
    comments_details = pd.DataFrame(comment_details)
    videos_details['published_At'] = pd.to_datetime(videos_details['published_At'])
    videos_details['published_At'] = videos_details['published_At'].dt.strftime('%Y-%m-%d %H:%M:%S')
    comments_details["comment_publishedAt"] = pd.to_datetime(comments_details["comment_publishedAt"])
    comments_details["comment_publishedAt"] = comments_details["comment_publishedAt"].dt.strftime('%Y-%m-%d %H:%M:%S')

tab1, tab2, tab3 = st.tabs(["migarte to mongodb", 'migrate to sql', 'Queries'])
with tab1:
    if st.button("migarte to Mongodb"):
        data = {"channel_data": channel_data, "playlist_details": playlist_details, "video_deatils": video_details,
                "comment_details": comment_details}
        client = MongoClient(
            "mongodb://localhost:27017")
        mydb = client["youtube_data"]
        mycol = mydb["channel_details"]
        mycol.insert_one(data)
        st.success("Migrated Successfully", icon="✅")
with tab2:
    if st.button("migrate to SQL"):
        mydb = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password='Apple123',
            auth_plugin="mysql_native_password")
        mycursor = mydb.cursor()
        mycursor.execute("USE youtube_data")
        c = "CREATE TABLE if not exists Channel_details (channel_id varchar(250),channel_name varchar(250),subcription_count int,channel_views bigint,channel_description TEXT ,playlist_id varchar(250),video_count int)"
        mycursor.execute(c)
        for index, row in channels_data.iterrows():
            query = "INSERT INTO youtube_data.Channel_details(channel_id,channel_name,subcription_count,channel_views,channel_description,playlist_id,video_count)values(%s,%s,%s,%s,%s,%s,%s)"
            mycursor.execute(query, (
            row.channel_id, row.channel_name, row.subscription_count, row.channel_views, row.channel_description,
            row.playlist_id, row.video_count))
        p = "create table if not exists playlist_details(playlist_id varchar(250),channel_id varchar(250),playlist_name varchar(250))"
        mycursor.execute(p)
        for index, row in playlists_details.iterrows():
            query = "insert into youtube_data.playlist_details(playlist_id,channel_id,playlist_name)values(%s,%s,%s)"
            mycursor.execute(query, (row.playlist_id, row.channel_id, row.playlist_name))
        v = "create table if not exists video_details(video_id varchar(250),playlist_ids varchar(255),video_name varchar(250),published_At datetime,video_description TEXT,view_count int,like_count int,favorite_count int,Thumnails varchar(250),comment_count int,caption_status varchar(250),duration TIME)"
        mycursor.execute(v)
        for index, row in videos_details.iterrows():
            query = "insert into youtube_data.video_details(video_id,playlist_ids,video_name,published_At,video_description,view_count,like_count,favorite_count,Thumnails,comment_count,caption_status,duration)values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            mycursor.execute(query, (
            row.video_id, row.playlist_id, row.video_name, row.published_At, row.video_description, row.view_count,
            row.like_count, row.favorite_count, row.Thumnails, row.comment_count, row.caption_status, row.duration))
        cmd = "create table if not exists comment_details(comment_id varchar(250),comment_text TEXT,comment_author varchar(250),comment_publishedAt datetime)"
        mycursor.execute(cmd)
        for index, row in comments_details.iterrows():
            query = "insert into youtube_data.comment_details(comment_id,comment_text,comment_author,comment_publishedAt)values(%s,%s,%s,%s)"
            mycursor.execute(query, (row.comment_id, row.comment_text, row.comment_author, row.comment_publishedAt))
        mydb.commit()
        st.success("Migrated Successfully", icon="✅")
with tab3:
    q1 = 'What are the names of all the videos and their corresponding channels'
    q2 = 'Which channels have the most number of videos, and how many videos do they have?'

    q3 = 'What are the top 10 most viewed videos and their respective channels?'

    q4 = 'How many comments were made on each video, and what are their corresponding video names?'

    q5 = 'Which videos have the highest number of likes, and what are their corresponding channel names?'

    q6 = 'What is the total number of likes and dislikes for each video, and what are their corresponding video names?'

    q7 = 'What is the total number of views for each channel, and what are their corresponding channel names?'

    q8 = 'What are the names of all the channels that have published videos in the year 2023?'

    q9 = 'What is the average duration of all videos in each channel, and what are their corresponding channel names?'

    q10 = 'Which videos have the highest number of comments, and what are their corresponding channel names?'
    details = st.selectbox('please select query', (q1, q2, q3, q4, q5, q6, q7, q8, q9, q10))
    clicked = st.button("Get Answer")
    if clicked:
        mydb = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password='Apple123',
            auth_plugin="mysql_native_password")
        mycursor = mydb.cursor()
        mycursor.execute("USE youtube_data")
        if details == q1:
            query = "select c.channel_name,v.video_name from channel_details as c join video_details as v on c.playlist_id=v.playlist_ids "
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=["channel_names", "video_name"])
            st.write(df)
        elif details == q2:
            query = "select c.channel_name,c.video_count from channel_details as c"
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=['channel_names', 'video-count'])
            st.write(df)
        elif details == q3:
            query = 'select c.channel_name,v.view_count from channel_details as c join video_details as v order by v.view_count desc limit 10'
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=["channel_names", "most viewed top 10"])
            st.write(df)
        elif details == q4:
            query = 'select v.video_name,v.comment_count from video_details as v'
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=["video_names", "comment_counts"])
            st.write(df)
        elif details == q5:
            query = 'select c.channel_name,v.video_name,v.like_count from channel_details as c join video_details as v on c.playlist_id=v.playlist_ids order by v.like_count desc'
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=["channel_name", 'video_names', 'like_counts'])
            st.write(df)
        elif details == q6:
            query = 'select v.video_name,v.like_count from video_details as v '
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=['video_names', 'like_counts'])
            st.write(df)
        elif details == q7:
            query = 'select c.channel_name,c.channel_views from channel_details as c '
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=['channel_name', 'total_number_views'])
            st.write(df)
        elif details == q8:
            query = 'select c.channel_name,v.published_At from channel_details as c join video_details as v on v.playlist_ids=c.playlist_id where v.published_At like "2023%"'
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=["channel_name", "video_published at 2023"])
            st.write(df)
        elif details == q9:
            query = "select avg(v.duration) as duration,c.channel_name from video_details as v join channel_details as c group by c.channel_name order by duration desc"
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=['average_duration', 'channel_names'])
            st.write(df)
        elif details == q10:
            query = 'select c.channel_name,v.comment_count,v.video_name from channel_details as c inner join video_details as v on c.playlist_id=v.playlist_ids order by comment_count desc'
            mycursor.execute(query)
            results = mycursor.fetchall()
            df = pd.DataFrame(results, columns=['channel_name', 'highest_comment_counts', 'video_name'])
            st.write(df)
        mydb.commit()
