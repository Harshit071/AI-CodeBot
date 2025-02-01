from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import SignUpForm
from .models import Code
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LANG_LIST = [
    'c', 'cpp', 'csharp', 'css', 'dart', 'django', 'go', 'html',
    'java', 'javascript', 'matlab', 'mongodb', 'objectivec', 'perl',
    'php', 'powershell', 'python', 'r', 'regex', 'ruby', 'rust',
    'sass', 'scala', 'sql', 'swift', 'yaml'
]

def handle_gpt_request(request, prompt_template, template_name):
    if request.method == "POST":
        code = request.POST.get('code', '')
        lang = request.POST.get('lang', '')
        
        if not lang or lang == "Select Programming Language":
            messages.error(request, "Please select a programming language")
            return render(request, template_name, {
                'lang_list': LANG_LIST, 
                'code': code,
                'lang': lang
            })
            
        try:
            response = client.chat.completions.create(
                model="whisper-1",
                messages=[{
                    "role": "user", 
                    "content": prompt_template.format(lang=lang, code=code)
                }],
                temperature=0.2,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            if request.user.is_authenticated:
                Code.objects.create(
                    question=code,
                    code_answer=result,
                    language=lang,
                    user=request.user
                )
            
            return render(request, template_name, {
                'lang_list': LANG_LIST,
                'response': result,
                'lang': lang,
                'code': code
            })
            
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
            return render(request, template_name, {
                'lang_list': LANG_LIST,
                'code': code,
                'lang': lang
            })
    
    return render(request, template_name, {'lang_list': LANG_LIST})

def home(request):
    return handle_gpt_request(
        request,
        "Fix this {lang} code: {code}",
        'home.html'
    )

def suggest(request):
    return handle_gpt_request(
        request,
        "Provide suggestions for improving this {lang} code: {code}",
        'suggest.html'
    )

@require_POST
def login_user(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)
        messages.success(request, "Logged in successfully!")
    else:
        messages.error(request, "Invalid username or password")
    
    return redirect('home')

def logout_user(request):
    logout(request)
    messages.success(request, "Successfully logged out!")
    return redirect('home')

def register_user(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below")
    else:
        form = SignUpForm()
    
    return render(request, 'register.html', {"form": form})

@login_required
def past(request):
    code_entries = Code.objects.filter(user=request.user).order_by('-id')
    return render(request, 'past.html', {"code": code_entries})

@login_required
@require_POST
def delete_past(request, past_id):
    try:
        entry = Code.objects.get(id=past_id, user=request.user)
        entry.delete()
        messages.success(request, "Entry deleted successfully")
    except Code.DoesNotExist:
        messages.error(request, "Entry not found")
    return redirect('past')