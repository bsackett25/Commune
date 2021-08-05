from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Volunteer(db.Model):
	volunteer_id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(120), nullable=False, unique=True)
	password = db.Column(db.String(120), nullable=False)

	def __init__(self, user, password):
		self.username = user
		self.password = password

	def __repr__(self):
		return '<Volunteer {}>'.format(self.username)

class Organization(db.Model):
	organization_id = db.Column(db.Integer, primary_key=True)
	organization_name = db.Column(db.String(255), nullable=False)
	username = db.Column(db.String(120), nullable=False, unique=True)
	password = db.Column(db.String(120), nullable=False)

	hosting = db.relationship('Event', backref='host', lazy='dynamic')

	def __init__(self, user, password, name):
		self.username = user
		self.password = password
		self.organization_name = name

	def __repr__(self):
		return '<Organization Username {}, Display Name {}>'.format(self.username, self.organization_name)

guest_list = db.Table('attending',
	db.Column('attendee_id', db.Integer, db.ForeignKey('volunteer.volunteer_id')),
	db.Column('event_id', db.Integer, db.ForeignKey('event.event_id')
	)
)

class Event(db.Model):
	event_id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(120), nullable=False)
	description = db.Column(db.String(255), nullable=False)
	start_time = db.Column(db.DateTime, nullable=False)
	end_time = db.Column(db.DateTime, nullable=False)

	attendees = db.relationship('Volunteer', secondary=guest_list, backref='attending', lazy='dynamic')
	host_id = db.Column(db.Integer, db.ForeignKey('organization.organization_id'), nullable=False)
	host_name = db.Column(db.String(255), nullable=False)

	def __init__(self, title, description, start_time, end_time, host, host_name):
		self.title = title
		self.description = description
		self.start_time = start_time
		self.end_time = end_time
		self.host_id = host
		self.host_name = host_name

	def __repr__(self):
		return 'Event: {}, Host: {}, Description: {}, Starts: {}, Ends: {}'.format(self.title, self.host_name, self.description, self.start_time, self.end_time)
