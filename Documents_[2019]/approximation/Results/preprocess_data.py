import os
from util.data import Data

# Given a list of lists, transpose it and return.
def transpose(l): return [list(row) for row in zip(*l)]

# Given a count, return "count" evenly spaced points on the 
# unit circle in 2 dimensions.
def circle_points(n=12):
    import numpy as np
    radians = np.linspace(0, 2*np.pi, n+1)[:-1]
    points = [(float(np.cos(r)), float(np.sin(r))) for r in radians]
    return points

# Given a string date "year-month-day" convert it to a triple
#  (time, year_x, year_y) where "_x" and "_y" are coordinates on a circle.
def date_to_triple(date):
    import numpy as np
    year, month, day = map(int, date.split("-"))
    # Given three integers, return the percentage through the year.
    def to_0_1(year, month, day):
        # Code the number of days in each month.
        days = {m:31 for m in range(12)}
        days[4] = days[6] = days[9] = days[11] = 30
        days[2] = 28 + (not year%4)
        # Record the total number of days in the year.
        total_days = 365 + (not year%4)
        # Count how many days have elapsed.
        elapsed = 0
        for i in range(1, month): elapsed += days[i]
        elapsed += day
        return elapsed / total_days

    # Get the time on a real line.
    progress = to_0_1(year, month, day)
    time = year + progress
    x = np.cos( progress * 2 * np.pi )
    y = np.sin( progress * 2 * np.pi )
    return (time, float(x), float(y))

# Given a cardinal direction string return unit circle coordinates.
def cardinal_to_circle(card):
    directions = ["E", "ENE", "NE", "NNE", "N", "NNW", "NW", "WNW", 
                  "W", "WSW", "SW", "SSW", "S", "SSE", "SE", "ESE"]
    try:    return circle_points(len(directions))[ directions.index(card) ]
    except: return (None, None)


# Read in the data files.
cwd = os.path.dirname(os.path.abspath(__file__))
raw_dir = os.path.join( cwd, "Raw" )
data_dir = os.path.join( cwd, "Data" )

for raw_file in sorted(os.listdir(raw_dir)):
    raw_path = os.path.join(raw_dir, raw_file)
    data_path = os.path.join(data_dir, raw_file + '.dill')
    if not os.path.exists(data_path):
        print('-'*70)
        print(raw_path)
        d = Data.load(raw_path, sep=",", verbose=True)    
        if   (raw_file == "creditcard.csv"):
            # Remove all fraudulent transactions, only keep authentic ones.
            # Only need to remove the "time" 1st column and "fraud" last column.
            print("Removing fraudulent transations..")
            d = d[d[d.names[-1]] == "0"]
            print("Reducing data..")
            d = d[ :len(d)//50, d.names[1:-1] ]
            print("Finding unique points..")
            unique_points = {}
            for i,pt in enumerate(d):
                pt = tuple(pt[:-1])
                unique_points[pt] = unique_points.get(pt, []) + [i]
            # Store the indices of the first occurrence of each unique point.
            unique_indices = sorted(unique_points[pt][0] for pt in unique_points)
            print(f"Removing {len(d) - len(unique_indices)} duplicate points..")
            d = d[unique_indices]
        elif (raw_file == "forestfires.csv"):
            # Map months to a circle, remove the day of week information.
            months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            month_map = {m:pt for m,pt in zip(months, circle_points(len(months)))}
            d["month_x"] = (month_map[v][0] for v in d["month"])
            d["month_y"] = (month_map[v][1] for v in d["month"])
            d = d[[n for n in d.names if n not in ("month", "day", "area")] +["area"]]
        elif (raw_file == "iozone_150.csv"):
            # Reduce to the "readers" test type.
            d = d[d["Test"] == "readers"]
            d = d[[n for n in d.names if n != "Test"]]
            # Convert the distributions to an object that supports
            # addition, multiplication by floats, and difference.
            trial_cols = [n for n in d.names if "Trial" in n]
            from util.stats import cdf_fit
            print("Fitting distributions..")
            d["Throughput"] = [cdf_fit(row, fit="cubic") for row in d[:,trial_cols]]
            print("Reducing data..")
            d = d[[n for n in d.names if "Trial" not in n]]
        elif (raw_file == "parkinsons_updrs.csv"):
            # Remove the "subject#" 1st column.
            d.reorder([n for n in d.names if n not in {"total_UPDRS", "motor_UPDRS"}])
            d = d[d.names[1:-2] + ["total_UPDRS"]]
        elif (raw_file == "weatherAUS.csv"):
            # Count the occurrence of different locations in data.
            print()
            print("Choices for locations:")
            locs = [(sum(v == l for v in d["Location"]), l)
                    for l in sorted(set(d["Location"]))]
            locs.sort()
            print()
            for l in locs: print("",l)
            print()
            # Reduce to only the chosen location with most data.
            d = d[d["Location"] == locs[-2][1]]
            to_remove = {"Date", "Location", "WindGustDir", "WindGustSpeed", 
                         "WindDir9am", "WindDir3pm", "RainToday", "RainTomorrow"}
            # Replace all "NA" values with "None" values, convert to floats.
            for n in d.names:
                if (n in to_remove): continue
                d[n] = ((None if v == "NA" else float(v)) for v in d[n])
            # Correct the time attributes to be geometrically meaningful.
            d["Year"], d["Year X"], d["Year Y"] = transpose(
                (date_to_triple(date) for date in d["Date"]))
            # Convert wind directions into meaningful coordinates.
            d["WindDir9am X"], d["WindDir9am Y"] = transpose(
                (cardinal_to_circle(direction) for direction in d["WindDir9am"]))
            d["WindDir3pm X"], d["WindDir3pm Y"] = transpose(
                (cardinal_to_circle(direction) for direction in d["WindDir3pm"]))
            # Fill in the "Rain Tomorrow" column with appropriatae values.
            d["Rainfall Tomorrow"] = [d[i+1,"Rainfall"] for i in range(len(d)-1)] + [None]
            # Remove the rows that have missing values.
            d = d[(i for i in range(len(d)) if all(v != type(None) for v in map(type,d[i])))]
            # Remove the extra columns thata we don't want.
            d = d[[n for n in d.names if n not in to_remove]]
        d.save(data_path)
        print(d)
        print()
