# Используем официальный образ Home Assistant в качестве базового
FROM ghcr.io/home-assistant/home-assistant:stable

# Устанавливаем рабочую директорию
WORKDIR /custom_components

# Копируем содержимое папки custom_components в папку конфигурации Home Assistant
COPY ./energomera /energomera

