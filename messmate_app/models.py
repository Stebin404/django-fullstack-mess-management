from django.db import models
from django.utils import timezone


class SystemSettings(models.Model):
    Monthly_Price = models.FloatField(default=5000.0)

    def __str__(self):
        return f"System Settings"


class Student(models.Model):
    Student_ID = models.AutoField(primary_key=True)
    First_Name = models.CharField(max_length=100)
    Last_Name = models.CharField(max_length=100)
    Gender = models.CharField(max_length=10)
    DOB = models.DateField()
    Street = models.CharField(max_length=200)
    City = models.CharField(max_length=100)
    Pincode = models.CharField(max_length=10)
    Contact_No = models.CharField(max_length=15)
    Email = models.EmailField()
    Course = models.CharField(max_length=100)
    Room_No = models.CharField(max_length=10)

    Username = models.CharField(max_length=100, unique=True)
    Password = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.First_Name} {self.Last_Name}"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Rejected', 'Rejected'),
        ('Cancellation Pending', 'Cancellation Pending'),
        ('Cancellation Rejected', 'Cancellation Rejected'),
        ('Cancelled', 'Cancelled'),
    ]

    Subscription_ID = models.AutoField(primary_key=True)
    Student = models.ForeignKey(Student, on_delete=models.CASCADE)
    Plan_Name = models.CharField(max_length=50)
    Monthly_Price = models.FloatField()
    Requested_On = models.DateField(default=timezone.localdate)
    Start_Date = models.DateField(null=True, blank=True)
    End_Date = models.DateField(null=True, blank=True)
    Status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.Student.First_Name} - {self.Plan_Name}"


class Today_Menu(models.Model):
    Date = models.DateField(unique=True)
    Breakfast = models.CharField(max_length=300)
    Lunch = models.CharField(max_length=300)
    Dinner = models.CharField(max_length=300)

    def __str__(self):
        return f"Menu for {self.Date}"


class Complaint(models.Model):
    Complaint_ID = models.AutoField(primary_key=True)
    Student = models.ForeignKey(Student, on_delete=models.CASCADE)
    Complaint_Text = models.TextField()
    Date = models.DateTimeField(default=timezone.now)
    Status = models.CharField(max_length=20, default="Pending")

    def __str__(self):
        return f"Complaint {self.Complaint_ID}"
