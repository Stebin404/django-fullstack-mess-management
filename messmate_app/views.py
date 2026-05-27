from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from datetime import datetime

from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta

from .models import (
    Student,
    Subscription,
    Today_Menu,
    Complaint,
    SystemSettings
)

# ---------------------------
# Helper utilities
# ---------------------------

def require_student_session(request):
    """Return student instance or redirect to login."""
    sid = request.session.get("student_id")
    if not sid:
        return None
    try:
        return Student.objects.get(Student_ID=sid)
    except Student.DoesNotExist:
        return None


def is_caterer_session(request):
    return request.session.get("user_type") == "caterer"


# ---------------------------
# STUDENT AUTH
# ---------------------------

def student_register(request):
    if request.method == "POST":
        uname = request.POST.get("username", "").strip()
        pwd = request.POST.get("password", "")
        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        gender = request.POST.get("gender", "").strip()
        dob = request.POST.get("dob")
        street = request.POST.get("street", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        contact = request.POST.get("contact_no", "").strip()
        email = request.POST.get("email", "").strip()
        course = request.POST.get("course", "").strip()
        room = request.POST.get("room_no", "").strip()

        if not (uname and pwd and first and last and dob):
            messages.error(request, "Please fill all required fields.")
            return render(request, "messmate_app/student_register.html")

        # Unique username
        if Student.objects.filter(Username=uname).exists():
            messages.error(request, "Username already exists.")
            return render(request, "messmate_app/student_register.html")

        hashed = make_password(pwd)

        Student.objects.create(
            First_Name=first,
            Last_Name=last,
            Gender=gender,
            DOB=dob,
            Street=street,
            City=city,
            Pincode=pincode,
            Contact_No=contact,
            Email=email,
            Course=course,
            Room_No=room,
            Username=uname,
            Password=hashed,
        )

        messages.success(request, "Registration successful. Please login.")
        return redirect('student_login')

    return render(request, "messmate_app/student_register.html")


def student_login(request):
    if request.method == "POST":
        uname = request.POST.get("username", "").strip()
        pwd = request.POST.get("password", "").strip()

        # Caterer login
        caterer_user = getattr(settings, "CATERER_USERNAME", "caterer")
        caterer_pass = getattr(settings, "CATERER_PASSWORD", "caterer123")

        if uname == caterer_user:
            if pwd == caterer_pass:
                request.session.flush()
                request.session['user_type'] = 'caterer'
                return redirect('caterer_dashboard')
            else:
                messages.error(request, "Incorrect password for Caterer.")
                return render(request, "messmate_app/student_login.html")

        # Student login
        try:
            student = Student.objects.get(Username=uname)
        except Student.DoesNotExist:
            messages.error(request, "No account found with this username.")
            return render(request, "messmate_app/student_login.html")

        if not check_password(pwd, student.Password):
            messages.error(request, "Incorrect password.")
            return render(request, "messmate_app/student_login.html")

        request.session.flush()
        request.session['user_type'] = 'student'
        request.session['student_id'] = student.Student_ID

        return redirect('student_dashboard')

    return render(request, "messmate_app/student_login.html")


def student_logout(request):
    request.session.flush()
    return redirect('student_login')


# ---------------------------
# STUDENT PAGES
# ---------------------------

def student_dashboard(request):
    student = require_student_session(request)
    if not student:
        return redirect('student_login')

    auto_expire_subscriptions(student)

    return render(request, "messmate_app/student_dashboard.html", {"student": student})


def student_details(request):
    student = require_student_session(request)
    if not student:
        return redirect('student_login')

    return render(request, "messmate_app/student_details.html", {
        "student": student
    })


def choose_plan(request):
    student = require_student_session(request)
    if not student:
        return redirect('student_login')

    # ❗ Prevent multiple subscriptions
    # Student CANNOT apply if existing plan is active/pending/cancellation pending
    existing = Subscription.objects.filter(
    Student=student,
    Status__in=["Pending", "Active", "Cancellation Pending"]
    )

    if existing.exists():
        messages.error(request, "You already have an active or pending subscription.")
        return redirect("subscription_status")


    # Load Monthly Price
    settings_obj, _ = SystemSettings.objects.get_or_create(id=1)
    base = settings_obj.Monthly_Price

    # Meal ratios
    ratio = {
        "B": 2,
        "L": 3,
        "D": 5
    }

    combos = {
        'B': 'Breakfast',
        'L': 'Lunch',
        'D': 'Dinner',
        'B+L': 'Breakfast + Lunch',
        'B+D': 'Breakfast + Dinner',
        'L+D': 'Lunch + Dinner',
        'B+L+D': 'Breakfast + Lunch + Dinner'
    }

    # Price calculation
    combo_prices = {}
    for key, label in combos.items():
        total = sum(ratio[p] for p in key.split('+'))
        price = (total / 10) * base     # ratio total = 10
        combo_prices[key] = {
            "label": label,
            "price": round(price, 2)
        }

    # Handle POST request
    if request.method == "POST":
        plan = request.POST.get("plan")
        start_date = request.POST.get("start_date")

        if plan not in combo_prices:
            messages.error(request, "Invalid plan selected.")
            return redirect('choose_plan')

        if not start_date:
            start_date = timezone.localdate()  # default today

    # Create Subscription but do not set End_Date yet
        Subscription.objects.create(
            Student=student,
            Plan_Name=plan,
            Monthly_Price=combo_prices[plan]["price"],
            Start_Date=start_date,
            Status="Pending"
         )

        messages.success(request, "Subscription request submitted.")
        return redirect('subscription_status')


    # Render the template
    return render(request, "messmate_app/choose_plan.html", {
        "combo_prices": combo_prices,
        "today": timezone.localdate()   # <-- IMPORTANT
    })

def subscription_status(request):
    student = require_student_session(request)
    if not student:
        return redirect('student_login')

    auto_expire_subscriptions(student)

    # Always get the most recent subscription by ID (most reliable)
    latest = Subscription.objects.filter(Student=student).order_by('-Subscription_ID').first()

    # Treat these statuses as "not current"
    NON_CURRENT_STATUSES = ["Cancelled", "Rejected", "Cancellation Rejected"]

    if latest and latest.Status not in NON_CURRENT_STATUSES:
        current = latest
    else:
        current = None

    # For history, show all subscriptions except the "current" one
    history = Subscription.objects.filter(Student=student).order_by('-Subscription_ID')

    # Handle POST actions
    if request.method == "POST":
        # Handle cancellation request
        if request.POST.get("cancel_request") and current:
            if current.Status == "Active":
                current.Status = "Cancellation Pending"
                current.save()
                messages.success(request, "Cancellation request sent.")
            else:
                messages.error(request, "You cannot cancel this subscription.")
            return redirect('subscription_status')
        
        # Handle delete request
        if request.POST.get("delete_subscription") and current:
            if current.Status in ["Pending", "Rejected"]:
                current.delete()
                messages.success(request, "Subscription deleted successfully.")
            else:
                messages.error(request, "You can only delete pending or rejected subscriptions.")
            return redirect('subscription_status')

    return render(request, "messmate_app/subscription_status.html", {
        "current": current,
        "history": history
    })




def todays_menu(request):
    today = timezone.localdate()
    menu = Today_Menu.objects.filter(Date=today).first()

    return render(request, "messmate_app/todays_menu.html", {
        "menu": menu,
        "date": today
    })



def submit_complaint(request):
    student = require_student_session(request)
    if not student:
        return redirect('student_login')

    if request.method == "POST":
        text = request.POST.get("complaint_text", "").strip()

        if not text:
            messages.error(request, "Complaint cannot be empty.")
            return redirect('submit_complaint')

        Complaint.objects.create(Student=student, Complaint_Text=text)
        messages.success(request, "Complaint submitted.")
        return redirect('student_dashboard')

    return render(request, "messmate_app/complaint.html")


# ---------------------------
# CATERER PAGES
# ---------------------------

def caterer_dashboard(request):
    if not is_caterer_session(request):
        return redirect('student_login')

    active = Subscription.objects.filter(Status="Active")

    breakfast_count = 0
    lunch_count = 0
    dinner_count = 0

    for s in active:
        parts = s.Plan_Name.split('+')   # Example: ["B", "L"]

        if "B" in parts:
            breakfast_count += 1
        if "L" in parts:
            lunch_count += 1
        if "D" in parts:
            dinner_count += 1

    return render(request, "messmate_app/caterer_dashboard.html", {
        "breakfast_count": breakfast_count,
        "lunch_count": lunch_count,
        "dinner_count": dinner_count,
    })



def update_menu(request):
    if not is_caterer_session(request):
        return redirect('student_login')

    today = timezone.localdate()

    if request.method == "POST":
        b = request.POST.get("breakfast", "")
        l = request.POST.get("lunch", "")
        d = request.POST.get("dinner", "")

        Today_Menu.objects.update_or_create(
            Date=today,
            defaults={"Breakfast": b, "Lunch": l, "Dinner": d}
        )

        messages.success(request, "Menu updated successfully.")
        return redirect('caterer_dashboard')

    menu = Today_Menu.objects.filter(Date=today).first()

    return render(request, "messmate_app/update_menu.html", {"menu": menu})


def manage_subscriptions(request):
    if not is_caterer_session(request):
        return redirect('student_login')

    # Handle actions
    if request.method == "POST":
        approve_id = request.POST.get("approve_id")
        reject_id = request.POST.get("reject_id")
        cancel_approve = request.POST.get("cancel_approve_id")
        cancel_reject = request.POST.get("cancel_reject_id")

        if approve_id:
            sub = Subscription.objects.get(Subscription_ID=approve_id)
            sub.Status = "Active"
            if not sub.Start_Date:
                sub.Start_Date = timezone.localdate()

            sub.End_Date = sub.Start_Date + timedelta(days=30)

            sub.save()
            messages.success(request, "Subscription approved.")
            return redirect('manage_subscriptions')

        if reject_id:
            sub = Subscription.objects.get(Subscription_ID=reject_id)
            sub.Status = "Rejected"
            sub.save()
            messages.success(request, "Subscription rejected.")
            return redirect('manage_subscriptions')

        if cancel_approve:
            sub = Subscription.objects.get(Subscription_ID=cancel_approve)
            sub.Status = "Cancelled"
            sub.End_Date = timezone.localdate()
            sub.save()
            messages.success(request, "Cancellation approved.")
            return redirect('manage_subscriptions')

        if cancel_reject:
            sub = Subscription.objects.get(Subscription_ID=cancel_reject)
            sub.Status = "Cancellation Rejected"
            sub.save()
            messages.success(request, "Cancellation rejected.")
            return redirect('manage_subscriptions')

    # Fetch lists
    pending = Subscription.objects.filter(Status="Pending")
    active = Subscription.objects.filter(Status="Active")
    cancel_pending = Subscription.objects.filter(Status="Cancellation Pending")

    return render(request, "messmate_app/manage_subscriptions.html", {
        "pending": pending,
        "active": active,
        "cancel_pending": cancel_pending,
    })


def view_complaints(request):
    if not is_caterer_session(request):
        return redirect('student_login')

    complaints = Complaint.objects.select_related("Student").order_by("-Date")

    return render(request, "messmate_app/view_complaints.html", {
        "complaints": complaints
    })


def caterer_details(request):
    return render(request, "messmate_app/caterer_details.html")


def update_monthly_price(request):
    if not is_caterer_session(request):
        return redirect('student_login')

    settings_obj, _ = SystemSettings.objects.get_or_create(id=1)

    if request.method == "POST":
        new_price = request.POST.get("monthly_price")
        try:
            new_price = float(new_price)
            settings_obj.Monthly_Price = new_price
            settings_obj.save()
            messages.success(request, "Monthly price updated.")
        except:
            messages.error(request, "Invalid number entered.")
        return redirect('update_monthly_price')

    return render(request, "messmate_app/update_monthly_price.html", {
        "current_price": settings_obj.Monthly_Price
    })
#Mothly price setting
settings_obj, _ = SystemSettings.objects.get_or_create(id=1)
base = settings_obj.Monthly_Price


def auto_expire_subscriptions(student):
    today = timezone.localdate()
    subs = Subscription.objects.filter(Student=student, Status="Active")

    for sub in subs:
        if sub.End_Date and sub.End_Date < today:
            sub.Status = "Expired"
            sub.save()