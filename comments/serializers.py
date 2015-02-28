from .models import Comment
from rest_framework import serializers


class PublicCommentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Comment
		fields = ('name', 'comment', 'website', 'created_date', 'permalink', 'reply_to')


class SubmitCommentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Comment
		fields = ('name', 'comment', 'website', 'email', 'permalink', 'reply_to')
