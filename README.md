GridPoint

GridPoint is a Python-based web application that uses mathematical optimization to help determine suitable warehouse locations based on demand and other location data.

Technologies Used

Backend

1. Python
2. Flask — web application server
3. SciPy — mathematical optimization, specifically scipy.optimize.milp

Frontend

1. HTML
2. CSS
3. JavaScript — embedded directly within the Python script
4. Leaflet — interactive maps
5. Chart.js — data visualization

Python Modules Used

Standard Python Modules

1. math
2. pathlib
3. os
4. csv
5. io
6. json
7. random
8. time
9. urllib

Third-Party Packages

1. flask
2. scipy
3. gunicorn

How to Run
1. Open the project folder

Open Command Prompt or Terminal and navigate to the folder containing the Python file.

For example:

cd "D:\New folder (9)\gridpoint"

2. Install the required dependencies

Run:

pip install flask scipy gunicorn

3. Run the application

Run:

python gridpoint_updated__5_ (1).py

4. Open the application

After the Flask server starts, the terminal should display a local address, usually similar to:

http://127.0.0.1:5000

Open that address in your web browser.

Notes

1. Make sure Python is installed and available from the command line.
2. An internet connection may be required for map tiles and other externally loaded frontend resources.
3. Keep the terminal running while using the application. Closing it or pressing Ctrl + C will stop the Flask server.
