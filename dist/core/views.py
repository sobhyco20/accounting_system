from django.shortcuts import render

def home_view(request):
    return render(request, 'home.html')


from django.shortcuts import render

def main_dashboard(request):
    return render(request, 'dashboard/main.html')
