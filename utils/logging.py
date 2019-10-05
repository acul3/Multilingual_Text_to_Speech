import random

import librosa.display
import matplotlib.pyplot as plt
from torch.utils.tensorboard import SummaryWriter

from utils import audio
from params.params import Params as hp


class Logger:
    @staticmethod
    def initialize_directory(logdir, to_console=True):
        Logger._sw = SummaryWriter(log_dir=logdir)
        Logger._to_console = to_console

    @staticmethod
    def progress(progress, prefix='', length=70):
        progress *= 100
        step = 100/length
        filled, reminder = int(progress // step), progress % step
        loading_bar = filled * '█'
        loading_bar += '░' if reminder < step / 3 else '▒' if reminder < step * 2/3 else '▓'
        loading_bar += max(0, length - filled) * '░' if progress < 100 else ''
        print(f'\r{prefix} {loading_bar} {progress:.1f}%', end=('' if progress < 100 else '\n'), flush=True)

    @staticmethod
    def training_progress(epoch, train_step, running_loss, learning_rate, progress):
        """Log running training epoch."""   
        Logger._sw.add_scalar("Loss/running", running_loss, train_step)
        if not Logger._to_console: return
        print('\r' + 70 * ' ', end='')
        Logger.progress(progress, f'epoch: {epoch:2d} ║ train loss: {running_loss:1.6f} │ lr: {learning_rate:1.6f} ║')

    @staticmethod
    def training(epoch, loss, learning_rate, duration):
        """Log training epoch."""
        if Logger._to_console:
            print('\r' + 70 * ' ', end='')
            print(f'\repoch: {epoch:2d} ║ train loss: {loss:1.6f} │ lr: {learning_rate:1.6f} ║ elapsed: {duration//60:d}:{duration%60:d} ║', end='', flush=True)
        Logger._sw.add_scalar("Loss/train", loss, epoch)
        Logger._sw.add_scalar("LearningRate/train", learning_rate, epoch)
        Logger._sw.add_scalar("Duration/train", duration, epoch)

    @staticmethod
    def skipped_evaluation():
        if Logger._to_console: print(flush=True)

    @staticmethod
    def evaluation(epoch, loss, learning_rate, target, prediction, stop_target, stop_prediction, alignment):
        """Log evaluation results."""
        if Logger._to_console:
            print(f'eval loss: {loss:1.6f} ║ lr: {learning_rate:1.6f}', flush=True)    
        Logger._sw.add_scalar("Loss/eval", loss, epoch)
        # show random output - spectrogram, stop token, alignment and audio
        idx = random.randint(0, alignment.size(0) - 1)
        predicted_melspec = prediction[idx].data.cpu().numpy()
        Logger._sw.add_figure("Alignment", Logger._plot_alignment(alignment[idx].data.cpu().numpy().T), epoch)    
        Logger._sw.add_figure("Stop", Logger._plot_stop_tokens(stop_target[idx].data.cpu().numpy(), stop_prediction[idx].data.cpu().numpy()), epoch) 
        Logger._sw.add_figure("Mel_target", Logger._plot_spectrogram(target[idx].data.cpu().numpy()), epoch)
        if predicted_melspec.shape[1] > 1:
            waveform = audio.inverse_mel_spectrogram(predicted_melspec) 
            Logger._sw.add_audio("Audio", waveform, epoch, sample_rate=hp.sample_rate)
            Logger._sw.add_figure("Mel_predicted", Logger._plot_spectrogram(predicted_melspec), epoch)


    @staticmethod
    def _plot_spectrogram(s):
        fig = plt.figure(figsize=(16, 4))
        librosa.display.specshow(s + hp.reference_spectrogram_db, x_axis='time', y_axis='mel', cmap='magma')
        plt.colorbar(format='%+2.0f dB')
        return fig

    @staticmethod
    def _plot_alignment(alignment):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        cax = ax.matshow(alignment, origin='lower')
        # fig.colorbar(cax, fraction=0.046, pad=0.04)
        plt.ylabel('Input index')
        plt.xlabel('Decoder step')
        plt.tight_layout() 
        return fig

    @staticmethod
    def _plot_stop_tokens(target, prediciton):
        fig = plt.figure(figsize=(14, 4))
        ax = fig.add_subplot(111)
        ax.scatter(range(len(target)), target, alpha=0.5, color='green', marker='+', s=1, label='target')
        ax.scatter(range(len(prediciton)), prediciton, alpha=0.5, color='red', marker='.', s=1, label='predicted')
        plt.xlabel("Frames (Green target, Red predicted)")
        plt.ylabel("Stop token probability")
        plt.tight_layout()
        return fig