from django.urls import reverse
from django.test import Client, TestCase
from django.contrib.auth import get_user_model

from posts.models import Post


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(username='testuser')
        cls.form_data = {
            'text': 'Test post',
            'username': 'testuser2',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в базе данных"""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}))

    def test_edit_post(self):
        """Валидная форма редактирования изменяет запись в базе данных"""
        post = Post.objects.create(text='Test post', author=self.user)
        new_text = 'Updated post'
        form_data = {
            'text': new_text,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': post.id}))
        post.refresh_from_db()
        self.assertEqual(post.text, new_text)

    def test_signup(self):
        """При отправке валидной формы создаётся новый пользователь"""
        users_count = get_user_model().objects.count()
        response = self.guest_client.post(
            reverse('users:signup'), data=self.form_data,
            follow=True)
        self.assertEqual(get_user_model().objects.count(), users_count + 1)
        self.assertRedirects(response, reverse('users:login'))
