# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.contrib.auth.models import User, UserManager
from django.db.models.signals import pre_save, post_save
from django.core.exceptions import ValidationError
import datetime, calendar
# Create your models here.

def get_image_path(instance, filename):
	return os.path.join('users', instance.id, filename) 


# Attaching a post_save signal handler to the Payment model to update the appropriate Contract
def update_contract_with_payments(sender, **kwargs):
	c = instance.contract
	c.update_with_payment(instance)

post_save.connect(update_contract_with_payments, sender="Payment")



class User(User):
	"""Custom User model, extending Django's default User"""
	USER_TYPES = (
		('MEM', 'Member'),
		('SPO', 'Sponsor'),
		('DON', 'Donation')
	) 
	
	profile_image = models.ImageField(upload_to=get_image_path, blank=True)
	utype = models.CharField(max_length=3, choices=USER_TYPES, default='MEM')
	
	objects = UserManager()

	@property
	def most_recent_payment(self):
		return self.payments.all()[0]

#	@property
#	def payments(self):
#		return self.payments_made.order_by('-for_year', '-for_month').all()
	
	def __unicode__(self):
		if self.first_name and self.last_name:
			return self.get_full_name()
		else:
			return self.username
			
			
			
class ContractType(models.Model):
	desc = models.CharField(max_length=128, blank=False, null=True)

	def __unicode__(self):
		return self.desc
		

class Contract(models.Model):
	CONTRACT_STATUSES = (
		('ACT', 'Active'),
		('LAP', 'Lapsed'),
		('TER', 'Terminated'),
		('PEN', 'Pending')
	)

	start = models.DateField()
	end = models.DateField()
	ctype = models.ForeignKey(ContractType, blank=False, null=True, verbose_name="Contract type")
	tier = models.ForeignKey("Tier", blank=False, null=True)
	user = models.ForeignKey(User, blank=False, null=True, related_name="contracts")
	status = models.CharField(max_length=3, choices=CONTRACT_STATUSES)
	
	# Takes a Payment object, calculates how many month's worth it is, and extends the contract end date accordingly
	def update_with_payment(self, p):
		if isinstance(p, Payment):
			# Get number of multiples of Contract for this Payment
			multiples = int(p.amount / self.tier.fee)
			
			# Get the future end month
			future_end_month = self.end.month + multiples
			jump_year = 0
			while future_end_month > 12: # Have we skipped a year end?
				future_end_month = future_end_month % 12
				jump_year += 1  # Keep counting how many years we're jumping ahead
			
			# Identify the last day of the future_end_month
			if jump_year:
				future_year = self.end.year + jump_year
			else:
				future_year = self.end.year
				
			future_last_day = calendar.monthrange(future_year, future_end_month)[1]
			
			# Update the end date for this Contract
			self.end = datetime.date(future_year, future_end_month, future_last_day)
			
			self.save()
			
		else:
			return False	
	
	
	def save(self):
		last_day = calendar.monthrange(self.end.year, self.end.month)[1]
		self.end = datetime.date(self.end.year, self.end.month, last_day)
		super(Contract, self).save()
	
	
	def __unicode__(self):
		return self.user.__unicode__() + u": " + self.ctype.__unicode__() + u" @ $" + unicode(self.tier.fee) + "/mth Start: " + u" " + unicode(self.start.strftime('%d %b %Y')) +  u" End: " + unicode(self.end.strftime('%d %b %Y'))
		

class Tier(models.Model):
	fee = models.FloatField(default=0.0)
	desc = models.CharField(max_length=255)
	
	def __unicode__(self):
		return self.desc + u": " + unicode(self.fee)


class Payment(models.Model):
	PAYMENT_METHODS = (
		('EFT', 'Electronic Fund Transfer'),
		('CHK', 'Cheque'),
		('CSH', 'Cash'),
		('OTH', 'Others')
	)
	
#	PAYMENT_TYPES = (
#		('DPT', 'Deposit'),
#		('FEE', 'Membership Fees'),
#		('DNT', 'Donation')
#	)

#	MONTHS = (
#		('1', 'Jan'),
#		('2', 'Feb'),
#		('3', 'Mar'),
#		('4', 'Apr'),
#		('5', 'May'),
#		('6', 'Jun'),
#		('7', 'Jul'),
#		('8', 'Aug'),
#		('9', 'Sep'),
#		('10', 'Oct'),
#		('11', 'Nov'),
#		('12', 'Dec')
#	)
	
#	@property
#	def year_range(self):
#		this_year = datetime.today().year
#		years = ( (unicode(this_year), unicode(this_year)) )
#		
#		for i in xrange(0, 10):
#			years.insert(0, (unicode(this_year-i), unicode(this_year-i)))
#			years.append((unicode(this_year+i), unicode(this_year+i)))
#			
#		return years

#	YEARS = (
#		('2010', '2010'),
#	)

	date_paid = models.DateField()
	amount = models.FloatField(default=0.0)
	method = models.CharField(max_length=3, choices=PAYMENT_METHODS, default='EFT')
	contract = models.ForeignKey(Contract, blank=False, null=True, related_name="payments")
	desc = models.CharField(max_length=255, blank=True)
	user = models.ForeignKey(User, blank=False, null=True, related_name="payments_made")
	
		
	def clean(self):
		# Model validation to ensure that Payment amount is multiple of Contract tier fee
		if (self.amount % self.contract.tier.fee) != 0:
			raise ValidationError(_("Payment amount is not a multiple of selected Contract's tier fee"))

	
	def __unicode__(self):
		return self.contract.__unicode__() + u" Paid: " + unicode(self.date_paid)
		


class Locker(models.Model):
	user = models.ForeignKey(User, blank=False, null=True, related_name="locker")
	num = models.IntegerField()
	