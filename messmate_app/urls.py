from django.urls import path
from . import views

urlpatterns = [

    # Student Auth
    path('student/register/', views.student_register, name='student_register'),
    path('student/login/', views.student_login, name='student_login'),
    path('student/logout/', views.student_logout, name='student_logout'),

    # Student Pages
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/details/', views.student_details, name='student_details'),
    path('student/choose-plan/', views.choose_plan, name='choose_plan'),
    path('student/subscription-status/', views.subscription_status, name='subscription_status'),
    path('student/todays-menu/', views.todays_menu, name='todays_menu'),
    path('student/complaint/', views.submit_complaint, name='submit_complaint'),

    # Caterer Pages
    path('caterer/dashboard/', views.caterer_dashboard, name='caterer_dashboard'),
    path('caterer/update-menu/', views.update_menu, name='update_menu'),
    path('caterer/manage-subscriptions/', views.manage_subscriptions, name='manage_subscriptions'),
    path('caterer/view-complaints/', views.view_complaints, name='view_complaints'),
    path('caterer/details/', views.caterer_details, name='caterer_details'),
    path('caterer/update-mp/', views.update_monthly_price, name='update_monthly_price'),
]

