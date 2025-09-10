import pytz
from datetime import datetime, timedelta

def check_availability():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    current_hour = now_est.hour
    current_day = now_est.weekday()

    if current_day == 1 and current_hour >= 4:  # Tuesday 4am onwards
        return True, now_est.strftime("%A")
    elif 1 < current_day < 4:  # All day Wednesday and Thursday until 7pm
        return True, now_est.strftime("%A")
    elif current_day == 4 and current_hour < 19:  # Thursday until 7pm
        return True, now_est.strftime("%A")
    else:
        return False, now_est.strftime("%A")
    

def get_current_week(current_date):
    date_week_dict = {
        '9/4/2025': 1,   # Week 1: Sep 5-9
        '9/11/2025': 2,  # Week 2: Sep 12-16
        '9/18/2025': 3,  # Week 3: Sep 19-23
        '9/25/2025': 4,  # Week 4: Sep 26-30
        '10/2/2025': 5,  # Week 5: Oct 3-7
        '10/9/2025': 6, # Week 6: Oct 10-14
        '10/16/2025': 7, # Week 7: Oct 17-21
        '10/23/2025': 8, # Week 8: Oct 24-28
        '10/30/2025': 9, # Week 9: Oct 31-Nov 4
        '11/6/2025': 10, # Week 10: Nov 7-11
        '11/13/2025': 11, # Week 11: Nov 14-18
        '11/20/2025': 12, # Week 12: Nov 21-25
        '11/27/2025': 13, # Week 13: Nov 28-Dec 2
        '12/4/2025': 14, # Week 14: Dec 5-9
        '12/11/2025': 15, # Week 15: Dec 12-16
        '12/18/2025': 16, # Week 16: Dec 19-23
        '12/25/2025': 17, # Week 17: Dec 26-30
        '1/1/2025': 18   # Week 18: Jan 2-6
    }
    # Convert the string dates to datetime objects
    date_week_dict_converted = {datetime.strptime(date, '%m/%d/%Y'): week for date, week in date_week_dict.items()}
    
    # Sort the dates in descending order
    sorted_dates = sorted(date_week_dict_converted.keys(), reverse=True)
    
    # Iterate through the sorted dates to find the corresponding week number
    for date in sorted_dates:
        if current_date >= date:
            return date_week_dict_converted[date]
    return None  # If current date is before all the dates in the dictionary
