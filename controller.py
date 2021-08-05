from flask import Flask, request, url_for, redirect, session, render_template
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import datetime

from models import db, Volunteer, Organization, Event

app = Flask(__name__)

app.config['SECRET_KEY']='a very secret secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///commune_events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #here to silence deprecation warning

db.init_app(app)

@app.cli.command('initdb')
def initdb_command():

    db.drop_all()
    db.create_all()

    print('Datebase Tables Initialized')

@app.route('/')
def default():
    return redirect(url_for("home_page"))

@app.route("/home")
def home_page():
    # if logged in, display list of events attending (Volunteer) or events hosting (Organization)
    hosting_list=[]
    attending_list=[]
    if "username" in session:
        if session['usertype'] == 'organization':
            hosting_list = Organization.query.filter_by(username=session['username']).first().hosting.order_by(Event.start_time)
        else:
            attending_list = Volunteer.query.filter_by(username=session['username']).first().attending

    # Display list of ALL events as well
    event_list = Event.query.order_by(Event.start_time).all()
    return render_template("home_page.html", events=event_list, hosting_ev=hosting_list, attending_ev=attending_list)

@app.route("/logout")
def logout():
    # Remove username and usertype from session to log out
    session.pop('username', None)
    session.pop('usertype', None)
    return redirect(url_for('home_page'))

# Adapter to convert HTML date object to Python datetime object
def process_date(date_in):
    return datetime.strptime(date_in, '%Y-%m-%dT%H:%M')

# Interface for creating an Event
@app.route("/create", methods=['GET', 'POST'])
def create_event():
    # Must be logged in as Organization usertype to access page
    # If not an organization, reroute to home page
    if "username" not in session:
        return redirect(url_for('home'))
    elif "usertype" in session:
        if session['usertype'] == 'volunteer':
            return redirect(url_for('home'))

    error = []
    if request.method == 'POST':
        # Check that Event has a title
        if request.form['title'] == "":
            error.append("Event must have a title")
        # Check that there isn't another event by the same name
        elif Event.query.filter_by(title=request.form['title']).first():
            error.append("This event title is already taken")
        # Check that Event has a start and end time
        elif request.form['start'] == "" or request.form['end'] == "":
            error.append("Event must have a start and end date")
        # Check that start time is actually before end time
        elif request.form['start'] >= request.form['end']:
            error.append("End Date must be after start date")
        else:
            # if no errors, add the new Event
            newEvent = Event(request.form['title'], request.form['desc'], process_date(request.form['start']), process_date(request.form['end']), Organization.query.filter_by(username=session['username']).first().organization_id, Organization.query.filter_by(username=session['username']).first().organization_name)
            db.session.add(newEvent)
            db.session.commit()
            return redirect(url_for('home_page'))
    if not error:
        error = None
    return render_template('create_event.html', err=error)

# Page for an organization to cancel an event
@app.route("/cancel", methods=['GET', 'POST'])
def cancel_event():
    if "username" not in session:
        return redirect(url_for('home'))
    elif "usertype" in session:
        if session['usertype'] == 'volunteer':
            return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        event_to_cancel = Event.query.filter_by(title=request.form['title']).first()
        if event_to_cancel:
            db.session.delete(event_to_cancel)
            db.session.commit()
        else:
            error = "Event '{}' does not exist".format(request.form['title'])

    events = Organization.query.filter_by(username=session['username']).first().hosting.order_by(Event.start_time)
    return render_template('cancel_event.html', events=events, error=error)

# Page for Volunteer to attend an event
@app.route("/attend", methods=['GET', 'POST'])
def attend_event():
    # If not logged in as a volunteer, then redirect to home page
    if "username" not in session:
        return redirect(url_for('home'))
    elif "usertype" in session:
        if session['usertype'] == 'organization':
            return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        event = Event.query.filter_by(title=request.form['title']).first()
        if event:
            # Add Volunteer to attending roster
            event.attendees.append(Volunteer.query.filter_by(username=session['username']).first())
            db.session.commit()
        else:
            error = "You may not attened a event that does not exist. Please check your spelling"

    # display events available
    events = Event.query.all()
    return render_template('attend_event.html', events=events, error=error)

# Portal to direct user to Volunteer login or Organization Log in
@app.route("/login")
def login_portal():
    # If already logged in, reroute to home page
    if "username" in session:
        return redirect(url_for('home'))

    return render_template('login_portal.html')

# Volunteer login, interfaces with Volunteer database table
@app.route("/login_volunteer", methods=['GET', 'POST'])
def login_volunteer():
    # If already logged in, reroute to home page
    if "username" in session:
        return redirect(url_for('home'))

    failed = False
    if request.method == 'POST':
        # Check username
        user_exists = Volunteer.query.filter_by(username=request.form["user"]).first()
        if user_exists:
            # Check hashed password
            if check_password_hash(user_exists.password, request.form['pass']):
                # If credentials are found in the table, then log in session
                session["username"] = user_exists.username
                session["usertype"] = 'volunteer'
                return redirect(url_for('home_page'))
        failed = True

    return render_template('login_volunteer.html', failure = failed)

# Organization Login, interfaces with Organization database table
@app.route("/login_organization", methods=['GET', 'POST'])
def login_organization():
    # If already logged in, reroute to home page
    if "username" in session:
        return redirect(url_for('home'))

    failed = False
    if request.method == 'POST':
        # Check username
        user_exists = Organization.query.filter_by(username=request.form["user"]).first()
        if user_exists:
            # Check hashed password
            if check_password_hash(user_exists.password, request.form['pass']):
                # If credentials are found in the table, then log in session
                session["username"] = user_exists.username
                session["usertype"] = 'organization'
                return redirect(url_for('home_page'))
        failed = True

    return render_template('login_organization.html', failure = failed)

# Register portal, leads user to Volunteer register or Organization register
@app.route("/register")
def register_portal():
    # If already logged in, reroute to home page
    if "username" in session:
        return redirect(url_for('home'))

    return render_template('register_portal.html')

# Register Volunteer interface, interacts with Volunteer table
@app.route("/register_volunteer",  methods=['GET', 'POST'])
def register_volunteer():
    # If already logged in, reroute to home page
    if "username" in session:
        return redirect(url_for('home_page'))

    un_taken = False
    blank = False
    if request.method == 'POST':
        # Check if inputs are empty
        if not request.form['user'] or not request.form['pass']:
            blank = True
        # check if inputs are whitespace
        if request.form['user'].isspace() or request.form['user'].isspace():
            blank = True
        # check if username is taken already
        org_taken = Organization.query.filter_by(username=request.form['user']).first()
        vol_taken = Volunteer.query.filter_by(username=request.form['user']).first()
        if org_taken or vol_taken:
            un_taken = True
        # if every check passed, then add user and log them in
        if not blank and  not un_taken:
            session['username'] = request.form['user']
            session['usertype'] = 'volunteer'
            # New Organization with SHA256 hashed password
            newVolunteer = Volunteer(request.form['user'], generate_password_hash(request.form['pass']))
            db.session.add(newVolunteer)
            db.session.commit();
            return redirect(url_for('home_page'))

    return render_template('register_volunteer.html', un_failure=un_taken, blank_failure=blank)

# Organization register interface, interacts with organization table
@app.route("/register_organization",  methods=['GET', 'POST'])
def register_organization():
    # If already logged in, reroute to home page
    if "username" in session:
        return redirect(url_for('home_page'))

    un_taken = False
    blank = False
    if request.method == 'POST':
        # Check if inputs are empty
        if not request.form['user'] or not request.form['pass'] or not request.form['displayName']:
            blank = True
        # check if inputs are whitespace
        if request.form['user'].isspace() or request.form['user'].isspace() or request.form['displayName'].isspace():
            blank = True
        # check if username is taken already
        org_taken = Organization.query.filter_by(username=request.form['user']).first()
        vol_taken = Volunteer.query.filter_by(username=request.form['user']).first()
        if org_taken or vol_taken:
            un_taken = True
        # if every check passed, then add user and log them in
        if not blank and  not un_taken:
            session['username'] = request.form['user']
            session['usertype'] = 'organization'
            # New Organization with SHA256 hashed password
            newOrganization = Organization(request.form['user'], generate_password_hash(request.form['pass']), request.form['displayName'])
            db.session.add(newOrganization)
            db.session.commit();
            return redirect(url_for('home_page'))

    return render_template('register_organization.html', un_failure=un_taken, blank_failure=blank)
