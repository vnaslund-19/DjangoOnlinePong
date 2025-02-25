# Generated by Django 4.2.19 on 2025-02-24 18:31

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PongGame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player1_id', models.UUIDField(blank=True, null=True)),
                ('player2_id', models.UUIDField(blank=True, null=True)),
                ('connected_players', models.JSONField(blank=True, default=list)),
                ('ready_players', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('finished', 'Finished')], default='pending', max_length=20)),
                ('game_key', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('board_width', models.IntegerField(default=700)),
                ('board_height', models.IntegerField(default=500)),
                ('player_height', models.IntegerField(default=50)),
                ('player_speed', models.IntegerField(default=5)),
                ('ball_side', models.IntegerField(default=10)),
                ('start_speed', models.FloatField(default=7.5)),
                ('speed_up_multiple', models.FloatField(default=1.02)),
                ('max_speed', models.IntegerField(default=20)),
                ('points_to_win', models.IntegerField(default=3)),
                ('player_positions', models.JSONField(default=dict)),
                ('ball_position', models.JSONField(default=dict)),
                ('player1_score', models.IntegerField(default=0)),
                ('player2_score', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
