from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.template import loader
from django.http import HttpResponse
from django.contrib.auth import authenticate,login,logout

# Create your views here.
def register_user(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = User.objects.filter(username=username)

        if user.exists():
            messages.error(request,'User with this username already exists')
            return redirect("/auth/register/")
        
        user = User.objects.create_user(username=username)
        user.set_password(password)
        user.save()
        
        messages.success(request,'User created successfully')
        return redirect('/problems/')
    
    template = loader.get_template('register.html')
    context = {}
    return HttpResponse(template.render(context,request))

def login_user(request):

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not User.objects.filter(username=username).exists():
            messages.error(request,'User with this username does not exist')
            return redirect('/auth/login/')
        
        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request,'invalid password')
            return redirect('/auth/login')
        

        login(request,user)
        # Clear all previous messages
        list(messages.get_messages(request))
        # Now add the new message
        messages.success(request, 'login successful')

        return redirect('/problems/')
    
    template = loader.get_template('login.html')
    context ={}
    return HttpResponse(template.render(context,request))

def logout_user(request):
    logout(request)
    list(messages.get_messages(request))  # Clear all previous messages
    messages.success(request, 'Logout successful')
    return redirect('/auth/login/')

def profile(request):
    if request.user.is_authenticated:
        template = loader.get_template('profile.html')
        context = {}
        return HttpResponse(template.render(context,request))
    else:
        messages.error(request,'You are not logged in')
        return redirect('/auth/login/')