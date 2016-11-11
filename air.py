import pandas as pd
import numpy as np
from datetime import date
from dateutil.rrule import rrule, DAILY

#open data file
air = pd.read_csv('_Live__Air_Quality_Sensor_Data.csv',index_col=False)


#change station to more readable name
air['station'] = air['Sensor Location Slug']
air.pop('Sensor Location Slug')

#set up pollutants and stations list (number = expected daily entries)
pollutants = ['NOx','NO','NO2','CO','PM10']
stations = [['guildhall',96],['londonrdaurn',96],['londonrdenc',24],['windsorbridge',24]]

#delete royalvicpark data (only 2 months of live data)
air = air[air['station'] != 'royalvicpark']

#create new date fields - to look for missing entries
air['DateTime'] = pd.to_datetime(air['DateTime'])
air['date_only'] = air['DateTime'].dt.strftime('%Y/%m/%d')
air['hour'] = air['DateTime'].dt.strftime('%H')

#create total failure dataframe
cols = ['station','date_only','error_type']
total_failure = pd.DataFrame(columns=cols)

#set start and end date for the data
a = date(2014, 8, 30)
b = date(2016, 11, 7)

#loop through each date in the range
for dt in rrule(DAILY, dtstart=a, until=b):

    new_date = dt.strftime("%Y/%m/%d")
    #temp dataframe with records for date, grouped by station
    new_air = air[air['date_only']==new_date]
    if len(new_air) == 0:
        #adds "all_day" error for station 'all' if no records on given date
        my_list = ['all',new_date,'all_day']
        total_failure.loc[len(total_failure)]= my_list
    by_station = new_air.groupby('station')
    for s in stations:
        if s[0] in by_station.groups:
            #if data exists for this station
            entries = by_station.get_group(s[0])
            #check if the entry count is as expected
            if len(entries) != s[1]:
                missing_entries = s[1] - len(entries)
                #ignore the problem if more entries than expected
                if missing_entries > 0:
                    #adds "some_slots" error for given date
                    my_list = [s[0],new_date,'some_slots']
                    total_failure.loc[len(total_failure)]= my_list
        else:
            #adds "all_day" error if no records for this station on given date
            if len(new_air)> 0:
                my_list = [s[0],new_date,'all_day']
                total_failure.loc[len(total_failure)]= my_list

#create part failure dataframe and additional errors for concatination
part_failure = pd.DataFrame()
cols = ['station','date_only','hour', 'pollutant','error_type']
errors = pd.DataFrame(columns=cols)

#loop through the pollutants
for p in pollutants:
    #add any null values to the errors dataframe
    errors = air[air[p].isnull()]
    errors = errors[['station', 'date_only','hour']].copy()
    errors['pollutant'] = p
    errors['error_type'] = 'null'
    #removes entries where sensors do not measure specific pollutants
    if p == 'PM10':
        errors.drop(errors[errors['station']=='guildhall'].index, inplace=True)
        errors.drop(errors[errors['station']=='londonrdaurn'].index, inplace=True)
    if p == 'CO':
        errors.drop(errors[errors['station']=='londonrdenc'].index, inplace=True)
        errors.drop(errors[errors['station']=='londonrdaurn'].index, inplace=True)
    #merge null will all errors
    part_failure = pd.concat([part_failure, errors])
    #do the same for negatives
    errors = air[air[p]<0]
    errors = errors[['station', 'date_only','hour']].copy()
    errors['pollutant'] = p
    errors['error_type'] = 'negative'
    part_failure = pd.concat([part_failure, errors])

#export to csv
total_failure.to_csv('air_total_failure.csv')
part_failure.to_csv('air_part_failure.csv')
