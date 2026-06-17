from django.core.management.base import BaseCommand
from ai_assistant.services.hf_inference import HuggingFaceInference


class Command(BaseCommand):
    help = 'Проверяет подключение Django к локальному LM Studio.'

    def handle(self, *args, **options):
        ai = HuggingFaceInference()
        self.stdout.write(f'Provider: {ai.provider}')
        self.stdout.write(f'Base URL: {ai.lmstudio_base_url}')
        self.stdout.write(f'Model: {ai.lmstudio_model}')
        answer = ai.generate(
            'Ответь одной короткой фразой: подключение LM Studio работает.',
            temperature=0.2,
            max_tokens=80,
        )
        if answer:
            self.stdout.write(self.style.SUCCESS(f'Ответ модели: {answer}'))
        else:
            self.stdout.write(self.style.ERROR('Модель не ответила. Проверь, что LM Studio запущен и модель загружена.'))
