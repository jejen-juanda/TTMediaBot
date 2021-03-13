import re
import traceback
from threading import Thread

from .player import Mode, State
from .track import Track

class ProcessCommand(object):
    def __init__(self, player, services, default_service):
        self.player = player
        self.services = services
        self.service = default_service
        self.commands_dict = {"p": self.play_pause, "s": self.stop, "m": self.mode,     "sb": self.seek_back, "sf": self.seek_forward, "r": self.rate, "v": self.volume, "u": self.play_by_url, "h": self.help, "n": self.next, "b": self.back}


    def __call__(self, message):
        try:
            command = re.findall("[a-z]+", message.split(" ")[0].lower())[0]
        except IndexError:
            return self.help()
        arg = " ".join(message.split(" ")[1::])
        try:
            if command in self.commands_dict:
                return self.commands_dict[command](arg)
            else:
                return _("Unknown command.\n") + self.help()
        except Exception as e:
            traceback.print_exc()
            return f"error: {e}"

    def play_pause(self, arg):
        """Текст справки play pause"""
        if arg:
            track_list = self.service.search(arg)
            if track_list:
                self.player.play(track_list)
            else:
                return _("not found")
        else:
            if self.player.state == State.Playing:
                self.player.pause()
            elif self.player.state == State.Paused:
                self.player.play


    def rate(self, arg):
        """Изменяет скорость"""
        if not arg:
            self.player._vlc_player.set_rate(1)
        try:
            rate_number = abs(float(arg))
            if rate_number > 0 and rate_number <= 4:
                self.player._vlc_player.set_rate(rate_number)
            else:
                return _("Speed must be from 1 to 4")
        except ValueError:
            return _("Введите число, используйте .")

    def play_by_url(self, arg):
        """Воиспроизводит поток по ссылке."""
        if len(arg.split("://")) == 2 and arg.split("://")[0] != "file":
            playing_thread = Thread(target=self.player.play, args=(Track(url=arg),))
            playing_thread.start()
        elif not arg:
            return self.help()
        else:
            return _("Введите коректный url или разрешённый протокол")

    def stop(self, arg):
        """Останавливает аудио"""
        self.player.stop()

    def volume(self, arg):
        """Изменяет Громкость"""
        try:
            volume = int(arg)
            if volume >= 0 and volume <= 100:
                self.player.set_volume(int(arg))
            else:
                return _("Громкость в диапозоне 1 100")
        except ValueError:
            return _("Недопустимое значение. Укажите число от 1 до 100.")

    def seek_back(self, arg):
        try:
            self.player.seek_back(arg)
        except ValueError:
            return _("Недопустимое значение. Укажите число от 1 до 100.")

    def seek_forward(self, arg):
        try:
            self.player.seek_forward(arg)
        except ValueError:
            return _("Недопустимое значение. Укажите число от 1 до 100.")

    def next(self, arg):
        try:
            playing_thread = Thread(target=self.player.next)
            playing_thread.start()
        except IndexError:
            return _("это последний трек")

    def back(self, arg):
        try:
            playing_thread = Thread(target=self.player.back)
            playing_thread.start()
        except IndexError:
            return _("Это первый трек")

    def mode(self, arg):
        mode_help = "current_ mode: {current_mode}\n{modes}".format(current_mode=self.player.mode.name, modes="\n".join(["{name} - {value}".format(name=i.name, value=i.value) for i in [Mode.Single, Mode.TrackList]]))
        if arg:
            try:
                mode = Mode(int(arg))
                self.player.mode = Mode(mode)
            except TypeError:
                return mode_help
        else:
            return mode_help

    mode.help = "ModeHelp"


    def help(self, arg=None):
        help_strings = []
        for i in list(self.commands_dict):
            try:
                help_strings.append(
                    "{}: {}".format(i, self.commands_dict[i].help)
                )
            except AttributeError:
                pass
        return "\n".join(help_strings)

    help.help = "Возращает справку"
