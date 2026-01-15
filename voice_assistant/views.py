from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import speech_recognition as sr
import pyttsx3
from queue_system.models import Queue

@login_required
def voice_interface(request):
    return render(request, 'voice_assistant/voice_interface.html')

@login_required
def process_voice(request):
    if request.method == 'POST' and request.FILES.get('audio'):
        # Get the audio file from the request
        audio_file = request.FILES['audio']

        # Save the audio file temporarily
        import os
        from django.conf import settings
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            # Initialize speech recognition
            recognizer = sr.Recognizer()

            # Load the audio file
            with sr.AudioFile(temp_file_path) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source)
                audio_data = recognizer.record(source)

            # Recognize speech
            try:
                text = recognizer.recognize_google(audio_data)
                print(f"Recognized text: {text}")

                # Process the recognized text and generate response
                response_text = process_voice_command(text, request.user)

                return JsonResponse({
                    'success': True,
                    'recognized_text': text,
                    'response': response_text
                })

            except sr.UnknownValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Could not understand audio. Please speak clearly.'
                })
            except sr.RequestError as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Speech recognition service unavailable: {e}'
                })

        except Exception as e:
            print(f"Error processing audio: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Error processing audio: {str(e)}'
            })

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    return JsonResponse({'success': False, 'error': 'No audio file provided'})

@login_required
def process_voice_text(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        text = data.get('text', '')

        if text:
            response_text = process_voice_command(text, request.user)
            return JsonResponse({
                'success': True,
                'response': response_text
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No text provided'
            })

    return JsonResponse({'success': False, 'error': 'Invalid request'})
    """Process voice commands and return appropriate responses"""
    text = text.lower()

    # Get user's active queues
    active_queues = Queue.objects.filter(
        user=user,
        status__in=['waiting', 'serving']
    )

    if 'queue' in text and ('number' in text or 'token' in text):
        if active_queues.exists():
            queue = active_queues.first()
            return f"Your token number is {queue.token_number} for {queue.service.name}"
        else:
            return "You don't have any active queues"

    elif 'status' in text:
        if active_queues.exists():
            queue = active_queues.first()
            return f"Your queue status is {queue.get_status_display()} for {queue.service.name}"
        else:
            return "You don't have any active queues"

    elif 'time' in text or 'waiting' in text:
        if active_queues.exists():
            queue = active_queues.first()
            # Calculate estimated waiting time (simplified)
            position = Queue.objects.filter(
                service=queue.service,
                status='waiting',
                token_number__lt=queue.token_number
            ).count()
            estimated_time = position * queue.service.avg_service_time
            return f"You are number {position + 1} in queue. Estimated waiting time: {estimated_time} minutes"
        else:
            return "You don't have any active queues"

    elif 'counter' in text or 'serving' in text:
        if active_queues.exists():
            queue = active_queues.first()
            serving_queues = Queue.objects.filter(
                service=queue.service,
                status='serving'
            )
            if serving_queues.exists():
                return f"Counter {serving_queues.first().counter_number or '1'} is currently serving"
            else:
                return "No counters are currently serving"
        else:
            return "You don't have any active queues"

    else:
        return "I can help you with: queue number, status, waiting time, or current counter information"

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

@login_required
def get_queue_info(request):
    # Get user's active queues
    active_queues = Queue.objects.filter(
        user=request.user,
        status__in=['waiting', 'serving']
    ).first()

    if active_queues:
        info = f"Your token number is {active_queues.token_number}. Status: {active_queues.get_status_display()}. Service: {active_queues.service.name}"
    else:
        info = "You have no active queues."

    return JsonResponse({'info': info})
