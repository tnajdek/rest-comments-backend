from .models import Comment
from rest_framework import serializers


class PublicCommentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Comment
		fields = ('id', 'author_name', 'comment', 'website', 'created_date', 'post_slug', 'reply_to')


class SubmitCommentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Comment
		fields = ('author_name', 'comment', 'website', 'email', 'post_slug', 'reply_to')


class ModerateCommentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Comment
		fields = ()