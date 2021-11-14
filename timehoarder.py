""" time hoarder """

import pytz
import holidays
import pandas as pd
import datetime as dt
import win32com.client
import matplotlib.pyplot as plt
from collections.abc import Generator

DAY_START = "08:00:00"
DAY_END = "17:00:00"

__version__ = "0.1.0"

# internal utils


def business_days(sdate: dt.datetime,
                  edate: dt.datetime) -> Generator[dt.datetime, None, None]:
    """ return business days (non-holiday weekdays) in date range, inclusive """
    date_range = edate - sdate
    usholidays = holidays.US()
    for i in range(date_range.days + 1):
        day = sdate + dt.timedelta(days=i)
        if (day.weekday() < 5) and (day not in usholidays):
            yield day


def get_app_end(app):
    """ return appointment end datetime for the same day as the start datetime """
    if app.end.date() == app.start.date():
        # if the start/end dates are on the same day, keep original end
        # datetime
        end = app.end
    else:
        # otherwise manually set the end datetime to EOD on the start date
        naive_end = dt.datetime.combine(
            app.start.date(), dt.datetime.max.time())
        utc = pytz.timezone('UTC')
        end = naive_end.replace(tzinfo=utc)
    return end


def add_event(start, subject, duration_min):
    """ add an event to the outlook calendar """
    outlook = win32com.client.Dispatch('Outlook.Application')
    appointment = outlook.CreateItem(1)  # 1=outlook appointment item
    appointment.Start = start
    appointment.Subject = subject
    appointment.Duration = duration_min
    appointment.ReminderSet = False
    appointment.ReminderMinutesBeforeStart = 0
    appointment.Save()
    return True

# timehoarder functions


def get_calendar(begin, end):
    """ return outlook calendar object restricted to date range, inclusive """
    outlook = win32com.client.Dispatch(
        'Outlook.Application').GetNamespace('MAPI')
    calendar = outlook.getDefaultFolder(9).Items
    calendar.IncludeRecurrences = True
    calendar.Sort('[Start]')
    restriction = "[Start] >= '" + begin.strftime('%m/%d/%Y') + "' AND [END] <= '" + (
        end + dt.timedelta(days=1)).strftime('%m/%d/%Y') + "'"
    calendar = calendar.Restrict(restriction)
    return calendar


def get_appointments(calendar):
    """ return dataframe containing appointment info """
    appointments = [app for app in calendar]
    cal_subject = [app.subject for app in appointments]
    cal_date = [app.start.date() for app in appointments]
    cal_start = [app.start for app in appointments]
    cal_end = [get_app_end(app) for app in appointments]
    cal_body = [app.body for app in appointments]
    cal_duration = [
        (get_app_end(app) -
         app.start).total_seconds() /
        3600 for app in appointments]
    df = pd.DataFrame({'subject': cal_subject,
                       'date': cal_date,
                       'start': cal_start,
                       'end': cal_end,
                       'duration': cal_duration,
                       'body': cal_body})
    df["start"] = df["start"].dt.tz_convert(None)
    df["end"] = pd.to_datetime(df["end"], utc=True).dt.tz_convert(None)
    df["date"] = df["date"].astype('str')
    return df


def check_meeting_load(appointments):
    """ return color-coded dataframe summarizing total meeting load per business day """
    summary = appointments.groupby(
        'date')['duration'].sum().to_frame().reset_index()
    begin = min(appointments['start'])
    end = max(appointments['end'])
    days = [x.strftime('%Y-%m-%d') for x in business_days(begin, end)]
    alldays = pd.DataFrame(days, columns=['date'])
    result = pd.merge(alldays, summary, how="left", on=["date"])
    result.fillna(0, inplace=True)
    result["weekday"] = result["date"].astype('datetime64').dt.strftime('%A')
    return result[['date', 'weekday', 'duration']
                  ].style.background_gradient(axis=0)


def flag_overbooked(appointments, max_daily_load):
    """ flag days that are over the meeting max daily load (in hours) """
    if isinstance(max_daily_load, int):
        max_daily_dict = {
            d: max_daily_load for d in [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday"]}
    else:
        max_daily_dict = max_daily_load
    flag_days = []
    df = check_meeting_load(appointments).data
    for day, ddf in df.groupby('weekday'):
        weekday_limit = max_daily_dict[day]
        flag = ddf[ddf['duration'] >= weekday_limit]['date'].tolist()
        flag_days.extend(flag)
    return df[df['date'].isin(flag_days)]


def hoard_time(overbooked, subject, hoard_hours=None,
               appointments=None, pref_am_pm=None):
    """ create calendar appts to block off time for focused work """
    for date in (overbooked['date'].tolist()):
        if hoard_hours:
            hoard_hours_td = dt.timedelta(hours=hoard_hours)
            df = appointments[appointments['date'] == date]
            startstr = f"{date} {DAY_START}"
            endstr = f"{date} {DAY_END}"
            startappt = {'subject': 'START OF DAY',
                         'date': date,
                         'start': pd.Timestamp(startstr),
                         'end': pd.Timestamp(startstr),
                         'duration': 0,
                         'body': ''}
            endappt = {'subject': 'END OF DAY',
                       'date': date,
                       'start': pd.Timestamp(endstr),
                       'end': pd.Timestamp(endstr),
                       'duration': 0,
                       'body': ''}
            df = df.append([startappt, endappt]).sort_values(by='end')
            df['diff'] = (
                df["start"] -
                df["end"].shift(1)).fillna(
                pd.Timedelta('0 days 00:00:00'))
            block_candidates = df[df['diff'] >= hoard_hours_td]
            if block_candidates.shape[0] > 0:
                if pref_am_pm == 'PM':
                    ascorder = False
                else:
                    ascorder = True
                hoard_data = (
                    block_candidates.sort_values(
                        by='start',
                        axis=0,
                        ascending=ascorder)).iloc[0]
                start_time = str(
                    (hoard_data['start'] - hoard_data['diff']).time())
                duration_min = hoard_hours * 60
                print(
                    f'Creating {hoard_hours} hour event starting at {start_time} on {date}')
            else:
                print(f'No available time blocks on {date}')
                continue
        else:
            start_time = DAY_START
            duration_min = 540
        start = f"{date} {start_time}"
        add_event(start, subject, duration_min)  # hoard all 9 hrs
    return
