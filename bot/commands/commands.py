import _thread
import os
import subprocess
import sys


from bot.player.enums import Mode, State
from bot import errors, translator, vars


class Command:
    def __init__(self, command_processor):
        self.player = command_processor.player
        self.ttclient = command_processor.ttclient
        self.service_manager = command_processor.service_manager
        self.module_manager = command_processor.module_manager


class HelpCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('Shows command help')

    def __call__(self, arg, user):
        return self.command_processor.help(arg, user)


class AboutCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Shows information about this bot')

    def __call__(self, arg, user):
        about_text = _('')
        return about_text


class PlayPauseCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('QUERY Plays tracks found for the query. If no query is given plays or pauses current track')

    def __call__(self, arg, user):
        if arg:
            self.ttclient.send_message(_('Searching...'), user)
            try:
                track_list = self.service_manager.service.search(arg)
                self.ttclient.send_message(_("{nickname} requested {request}").format(nickname=user.nickname, request=arg), type=2)
                self.player.play(track_list)
                return _('Playing {}').format(self.player.track.name)
            except errors.NothingFoundError:
                return _('Nothing is found for your query')
        else:
            if self.player.state == State.Playing:
                self.player.pause()
            elif self.player.state == State.Paused:
                self.player.play()


class RateCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('RATE Sets rate to a value from 0.25 to 4. If no rate is given shows current rate')

    def __call__(self, arg, user):
        if arg:
            try:
                rate_number = abs(float(arg))
                if rate_number >= 0.25 and rate_number <= 4:
                    self.player.set_rate(rate_number)
                else:
                    raise ValueError
            except ValueError:
                raise errors.InvalidArgumentError
        else:
            return str(self.player.get_rate())


class PlayUrlCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('URL Plays a stream from a given URL')

    def __call__(self, arg, user):
        if arg:
            try:
                tracks = self.module_manager.streamer.get(arg, user.is_admin)
                self.ttclient.send_message(_('{nickname} requested playing from a URL').format(nickname=user.nickname), type=2)
                self.player.play(tracks)
            except errors.IncorrectProtocolError:
                return _('Incorrect protocol')
            except errors.ServiceError:
                return _('Cannot get stream URL')
            except errors.PathNotFoundError:
                return _('The path cannot be found')
        else:
            raise errors.InvalidArgumentError


class StopCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Stops playback')

    def __call__(self, arg, user):
        if self.player.state != State.Stopped:
            self.player.stop()
            self.ttclient.send_message(_("{nickname} stopped playback").format(nickname=user.nickname), type=2)
        else:
            return _('Nothing is playing')


class VolumeCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('VOLUME Sets volume to a value from 0 to {max_volume}').format(max_volume=self.player.max_volume)

    def __call__(self, arg, user):
        if arg:
            try:
                volume = int(arg)
                if 0 <= volume <= self.player.max_volume:
                    self.player.set_volume(int(arg))
                else:
                    raise ValueError
            except ValueError:
                raise errors.InvalidArgumentError
        else:
            return str(self.player.volume)


class SeekBackCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('[STEP] Seeks current track back. the optional step is specified in percents from 1 to 100')

    def __call__(self, arg, user):
        if arg:
            try:
                self.player.seek_back(float(arg))
            except ValueError:
                raise errors.InvalidArgumentError
        else:
            self.player.seek_back()


class SeekForwardCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('[STEP] Seeks current track forward. the optional step is specified in percents from 1 to 100')

    def __call__(self, arg, user):
        if arg:
            try:
                self.player.seek_forward(float(arg))
            except ValueError:
                raise errors.InvalidArgumentError
        else:
            self.player.seek_forward()


class NextTrackCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Plays next track')

    def __call__(self, arg, user):
        try:
            self.player.next()
            return _('Playing {}').format(self.player.track.name)
        except errors.NoNextTrackError:
            return _('No next track')
        except errors.NothingIsPlayingError:
            return _('Nothing is currently playing')


class PreviousTrackCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Plays previous track')

    def __call__(self, arg, user):
        try:
            self.player.previous()
            return _('Playing {}').format(self.player.track.name)
        except errors.NoPreviousTrackError:
            return _('No previous track')
        except errors.NothingIsPlayingError:
            return _('Nothing is playing')


class ModeCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('MODE Sets playback mode. If no MODE is given shows a list of modes')
        self.mode_names = {Mode.SingleTrack: _('Single Track'), Mode.RepeatTrack: _('Repeat Track'), Mode.TrackList: _('Track list'), Mode.RepeatTrackList: _('Repeat track list'), Mode.Random: _('Random')}

    def __call__(self, arg, user):
        mode_help = 'current_ mode: {current_mode}\n{modes}'.format(current_mode=self.mode_names[self.player.mode], modes='\n'.join(['{value} {name}'.format(name=self.mode_names[i], value=i.value) for i in Mode.__members__.values()]))
        if arg:
            try:
                mode = Mode(arg.lower())
                self.player.mode = Mode(mode)
                return 'Current mode: {mode}'.format(mode=self.mode_names[self.player.mode])
            except ValueError:
                return 'Incorrect mode\n' + mode_help
        else:
            return mode_help


class ServiceCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('SERVICE Selects a service to play from. If no service is given shows current service and a list of available ones')

    def __call__(self, arg, user):
        service_help = 'Current service: {current_service}\nAvailable: {available_services}'.format(current_service=self.service_manager.service.name, available_services=', '.join([i for i in self.service_manager.available_services]))
        if arg:
            arg = arg.lower()
            if arg in self.service_manager.available_services:
                self.service_manager.service = self.service_manager.available_services[arg]
                return _('Current service: {}').format(self.service_manager.service.name)
            else:
                return _('Unknown service.\n{}').format(service_help)
        else:
            return service_help


class SelectTrackCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('NUMBER Selects track by number from the list of current results')

    def __call__(self, arg, user):
        if arg:
            try:
                number = int(arg)
                if number > 0:
                    index = number - 1
                elif number < 0:
                    index = number
                else:
                    return _('Incorrect number')
                self.player.play_by_index(index)
                return _('Playing {} {}').format(arg, self.player.track.name)
            except errors.IncorrectTrackIndexError:
                return _('Out of list')
            except errors.NothingIsPlayingError:
                return _('Nothing is currently playing')
            except ValueError:
                raise errors.InvalidArgumentError
        else:
            if self.player.state != State.Stopped:
                return _('Playing {} {}').format(self.player.track_index + 1, self.player.track.name)
            else:
                return _('Nothing is currently playing')


class GetLinkCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Gets a direct link to the current track')

    def __call__(self, arg, user):
        if self.player.state != State.Stopped:
            url = self.player.track.url
            if url:
                return url
            else:
                return _('URL is not available')
        else:
            return _('Nothing is currently playing')


class ChangeNicknameCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('NICKNAME Sets the bot\'s nickname')

    def __call__(self, arg, user):
        self.ttclient.change_nickname(arg)


class PositionCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    def __call__(self, arg, user):
        if arg:
            try:
                self.player.set_position(float(arg))
            except errors.IncorrectPositionError:
                return _('Incorrect position')
            except ValueError:
                return _('Must be integer')
        else:
            try:
                return str(round(self.player.get_position(), 2))
            except errors.NothingIsPlayingError:
                return _('Nothing is currently playing')

class VoiceTransmissionCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Enables or disables voice transmission')

    def __call__(self, arg, user):
        if not self.ttclient.is_voice_transmission_enabled:
            self.ttclient.enable_voice_transmission()
            if self.player.state == State.Stopped:
                self.ttclient.change_status_text(_('Voice transmission enabled'))
            return _('Voice transmission enabled')
        else:
            self.ttclient.disable_voice_transmission()
            if self.player.state == State.Stopped:
                self.ttclient.change_status_text('')
            return _('Voice transmission disabled')


class LockCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('Locks or unlocks the bot')

    def __call__(self, arg, user):
        return self.command_processor.lock(arg, user)

class VolumeLockCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('Locks or unlocks volume')

    def __call__(self, arg, user):
        return self.command_processor.volume_lock(arg, user)


class ChangeStatusCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('changes status of bot')


    def __call__(self, arg, user):
        self.ttclient.change_status_text(arg)



class SaveConfigCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('saves config to file')

    def __call__(self, arg, user):
        self.command_processor.config.save()
        return _('Config saved')

class AdminUsersCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('shows list of admin users, if user_name is given adds it to list')

    def __call__(self, arg, user):
        admin_users = self.command_processor.config['teamtalk']['users']['admins']
        if arg:
            if arg[0] == '+':
                admin_users.append(arg[1::])
                return _('Added')
            elif arg[0] == '-':
                try:
                    del admin_users[admin_users.index(arg[1::])]
                    return _('Deleted')
                except ValueError:
                    return _('This user is not admin')
        else:
            admin_users = admin_users.copy()
            if len(admin_users) > 0:
                if '' in admin_users:
                    admin_users[admin_users.index('')] = '<Anonymous>'
                return ', '.join(self.command_processor.config['teamtalk']['users']['admins'])
            else:
                return _('List is empty')


class BannedUsersCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('shows list of banned users, if user_name is given adds to/deletes from list')

    def __call__(self, arg, user):
        banned_users = self.command_processor.config['teamtalk']['users']['banned_users']
        if arg:
            if arg[0] == '+':
                banned_users.append(arg[1::])
                return _('Added')
            elif arg[0] == '-':
                try:
                    del banned_users[banned_users.index(arg[1::])]
                    return _('Deleted')
                except ValueError:
                    return _('This user is not banned')
        else:
            banned_users = banned_users.copy()
            if len(banned_users) > 0:
                if '' in banned_users:
                    banned_users[banned_users.index('')] = '<Anonymous>'
                return ', '.join(banned_users)
            else:
                return _('List is empty')


class HistoryCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('shows history of playing (64 last tracks)')

    def __call__(self, arg, user):
        if arg:
            try:
                self.player.play(list(self.player.history), start_track_index=int(arg))
            except ValueError:
                return _('must be integer')
            except IndexError:
                return _('Out of list')
        else:
            track_names = []
            for number, track in enumerate(self.player.history):
                if track.name:
                    track_names.append(f'{number}: {track.name}')
                else:
                    track_names.append(f'{number}: {track.url}')
            return '\n'.join(track_names) if track_names else _('List is empty')


class LanguageCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)
        self.command_processor = command_processor

    @property
    def help(self):
        return _('changes language of bot')

    def __call__(self, arg, user):
        if arg:
            try:
                translator.install_locale(arg, fallback=arg == 'en')
                self.command_processor.config['general']['language'] = arg
                self.ttclient.change_status_text('')
                return _('language has been changed')
            except:
                return _('Incorrect locale')
        else:
            return _('Current locale is {current_locale}. available locales: {available_locales}').format(current_locale=self.command_processor.config['general']['language'], available_locales=', '.join(translator.get_locales()))


class QuitCommand   (Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('Quits the bot')

    def __call__(self, arg, user):
        _thread.interrupt_main()

class RestartCommand(Command):
    def __init__(self, command_processor):
        super().__init__(command_processor)

    @property
    def help(self):
        return _('restarts bot')

    def __call__(self, arg, user):
        if sys.platform == 'win32':
            subprocess.Popen('"{exec_path}" {args}'.format(exec_path=sys.executable, args=' '.join(sys.argv)))
        else:
            subprocess.Popen('"{exec_path}" {args}'.format(exec_path=os.path.join(vars.directory, 'TTMediaBot.sh'), args=' '.join(sys.argv[1::])), shell=True)
        sys.exit()
