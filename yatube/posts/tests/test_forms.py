from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(username='testuser')
        cls.group1 = Group.objects.create(
            title='Test group 1',
            slug='test-group-1',
            description='Test group 1 description'
        )
        cls.group2 = Group.objects.create(
            title='Test group 2',
            slug='test-group-2',
            description='Test group 2 description'
        )
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
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post(self):
        """Валидная форма редактирования изменяет запись в базе данных"""
        post = Post.objects.create(
            text='Test post', author=self.user,
            group=self.group1
        )
        new_text = 'Updated post'
        form_data = {
            'text': new_text,
            'group': self.group2.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': post.id})
        )
        post.refresh_from_db()
        self.assertEqual(post.text, new_text)
        self.assertEqual(post.group, self.group2)
        self.assertNotIn(post, self.group1.group.all())
        self.assertIn(post, self.group2.group.all())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_signup(self):
        """При отправке валидной формы создаётся новый пользователь"""
        users_count = get_user_model().objects.count()
        response = self.guest_client.post(
            reverse('users:signup'), data=self.form_data,
            follow=True
        )
        self.assertEqual(get_user_model().objects.count(), users_count + 1)
        self.assertRedirects(response, reverse('users:login'))

    def test_unauthorized_user_cant_create_post(self):
        """Неавторизованный пользователь не может создать пост"""
        posts_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(
            response,
            f"{reverse('users:login')}?next={reverse('posts:post_create')}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauthorized_user_cant_edit_post(self):
        """Неавторизованный пользователь не может редактировать пост"""
        post = Post.objects.create(text='Test post', author=self.user)
        new_text = 'Updated post'
        form_data = {
            'text': new_text,
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            f"{reverse('users:login')}?next="
            f"{reverse('posts:post_edit', kwargs={'post_id': post.id})}"
        )
        post.refresh_from_db()
        self.assertEqual(post.text, 'Test post')
        self.assertEqual(response.status_code, HTTPStatus.OK)
