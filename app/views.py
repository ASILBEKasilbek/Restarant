from django.shortcuts import render
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import redirect,render
# Create your views here.
def index(request):
    return render(request, 'main.html')

def register(request):
    if request.method=="POST":
        form= UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request,user)
            return redirect('index')
    else:
        form=UserCreationForm()
    return render(request,'register.html',{'form':form})