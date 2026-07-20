from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def role_redirect(request):
    profile = request.user.profile
    if profile.role == 'admin':
        return redirect('admin_dashboard')
    elif profile.role == 'nurse':
        return redirect('nurse_dashboard')
    elif profile.role == 'cleaner':
        return redirect('cleaner_dashboard')
    return redirect('login')