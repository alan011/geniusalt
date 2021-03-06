# Generated by Django 2.0.7 on 2018-08-02 16:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geniusalt', '0007_auto_20180716_0631'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='includerelationship',
            name='r_included',
        ),
        migrations.RemoveField(
            model_name='includerelationship',
            name='r_instance',
        ),
        migrations.AddField(
            model_name='instance',
            name='included_instances',
            field=models.ManyToManyField(related_name='_instance_included_instances_+', to='geniusalt.Instance'),
        ),
        migrations.DeleteModel(
            name='IncludeRelationship',
        ),
    ]
