import io
import os
import time
import uuid
import wave
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QComboBox, QPushButton, QMessageBox
import numpy as np
import requests
import sounddevice as sd
import urllib3
import sys
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Token:
    """
    Класс для получения и управления токенами аутентификации и авторизации для взаимодействия с API SaluteSpeech.
    """
    
    _authdata: str | None = None
    _token: str | None = None
    _expires_in: int | None = None

    @classmethod
    def get_authdata(cls) -> str:
        """
        Возвращает данные аутентификации.

        Если `_authdata` еще не установлены, метод извлекает значение из переменной окружения `SALUTESPEECH_API_KEY`
        и сохраняет его в `_authdata`.

        Returns:
            str: Данные аутентификации.
        """
        if cls._authdata is None:
            cls._authdata = os.environ.get("SALUTESPEECH_API_KEY")
        return cls._authdata

    @classmethod
    def get_token(cls) -> str:
        """
        Возвращает текущий токен доступа.

        Если `_token` еще не установлен или если срок действия `_token` истек, метод запрашивает новый токен,
        вызывая метод `__request_for_new_token__`.

        Returns:
            str: Текущий токен доступа.
        """
        if cls._token is None or (
            cls._expires_in is not None
            and cls._expires_in < int(time.time() * 1000) - 2000
        ):
            cls._token, cls._expires_in = cls.__request_for_new_token__()
        return cls._token

    @classmethod
    def __request_for_new_token__(cls) -> tuple[str, int]:
        """
        Запрашивает новый токен доступа от API.

        Выполняет POST-запрос к API для получения нового токена. В случае успешного ответа сохраняет и возвращает токен и время его истечения.

        Returns:
            tuple[str, int]: Возвращает токен доступа и время истечения в миллисекундах Unix времени.

        Raises:
            Exception: Если запрос завершился неудачно.
        """
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {Token.get_authdata()}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"scope": "SALUTE_SPEECH_PERS"}  # Укажите необходимый scope здесь

        response = requests.post(url, headers=headers, data=data, verify=False)

        if response.status_code == 200:
            response_data = response.json()
            # expires_at указывает на Unix-время завершения действия Access Token в миллисекундах
            return response_data["access_token"], response_data["expires_at"]
        else:
            raise Exception("Failed to obtain token")



def speak(text: str, voice: str = "Александра"):
    """
    Синтезирует речь по заданному тексту и воспроизводит её.

    Параметры:
    text (str): Текст для синтеза речи.

    voice (str): Голос для синтеза речи. Допустимые значения:
        - "Наталья"
        - "Александра"
        - "Борис"
        - "Марфа"
        - "Тарас"
        - "Сергей"

        Значение по умолчанию: "Александра".

    Исключения:
    ValueError: Если указано недопустимое значение для параметра 'voice'.
    Exception: Если синтез речи не удался на стороне API.

    Примеры использования:
    speak("Привет, как дела?", voice="Александра")
    """
    valid_voices = {
        "Наталья": "Nec",
        "Александра": "Ost",
        "Борис": "Bys",
        "Марфа": "May",
        "Тарас": "Tur",
        "Сергей": "Pon",
    }
    if voice not in valid_voices.keys():
        raise ValueError(f"Недопустимое значение для параметра 'voice': {voice}. Допустимые значения: {', '.join(valid_voices.keys())}")
    # Получаем токен из класса Token
    token = Token.get_token()

    # URL для синтеза речи
    url = f"https://smartspeech.sber.ru/rest/v1/text:synthesize?voice={valid_voices[voice]}_24000"

    # Заголовки запроса
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/text"}

    # Выполняем POST запрос
    response = requests.post(url, headers=headers, data=text, verify=False)

    # Проверяем успешность запроса
    if response.status_code == 200:
        with wave.open(io.BytesIO(response.content), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            audio_data = wav_file.readframes(wav_file.getnframes())
            audio = np.frombuffer(audio_data, dtype=np.int16)
            sd.play(audio, samplerate=sample_rate, blocking=True)
    else:
        raise Exception("Failed to synthesize speech")
    

class Interface(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.text_input_label = QLabel('Введите стихотворение:', self)
        self.text_input = QLineEdit(self)
        layout.addWidget(self.text_input_label)
        layout.addWidget(self.text_input)

        self.combo_box_label = QLabel('Выберите голос:', self)
        self.combo_box = QComboBox(self)
        self.combo_box.addItems(['Наталья', 'Александра', 'Борис', 'Марфа', 'Тарас', 'Сергей'])
        layout.addWidget(self.combo_box_label)
        layout.addWidget(self.combo_box)

        self.speak_button = QPushButton('Озвучить стихотворение', self)
        self.speak_button.clicked.connect(self.onSpeak)
        layout.addWidget(self.speak_button)

        self.setLayout(layout)

        self.setWindowTitle('Учим стихи')
        self.setGeometry(300, 300, 400, 200)

    def onSpeak(self):
        text = self.text_input.text()
        voice = self.combo_box.currentText()
        try:
            speak(text, voice)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Произошла ошибка: {str(e)}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Interface()
    ex.show()
    sys.exit(app.exec_())
