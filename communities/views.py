# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import generics, permissions
from .forms import PostForm
from .models import Post
from .serializers import PostSerializer


def post_list_view(request):
    """게시글 목록을 조회하는 뷰"""
    posts = Post.objects.all()
    return render(request, 'posts/post_list.html', {'posts': posts})


@login_required
def post_create_view(request):
    """새로운 게시글을 생성하는 뷰"""
    if request.method == 'POST':
        form = PostForm(
            data=request.POST,
            files=request.FILES,
            user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, '게시글이 성공적으로 등록되었습니다.')
            return redirect('posts:post_list')
    else:
        form = PostForm()
    
    return render(request, 'posts/post_form.html', {'form': form})


@login_required
def post_detail_view(request, pk):
    """게시글의 상세 정보를 조회하는 뷰"""
    post = get_object_or_404(Post, pk=pk)
    post.views += 1
    post.save()
    
    return render(request, 'posts/post_detail.html', {'post': post})


@login_required
def post_update_view(request, pk):
    """게시글 정보를 수정하는 뷰"""
    post = get_object_or_404(Post, pk=pk)
    
    if post.user != request.user:
        messages.error(request, '수정 권한이 없습니다.')
        return redirect('posts:post_detail', pk=pk)

    if request.method == 'POST':
        form = PostForm(
            data=request.POST,
            files=request.FILES,
            instance=post
        )
        if form.is_valid():
            form.save()
            messages.success(request, '게시글이 성공적으로 수정되었습니다.')
            return redirect('posts:post_detail', pk=pk)
    else:
        initial_hashtags = ' '.join(ht.name for ht in post.hashtags.all())
        form = PostForm(
            instance=post,
            initial={'hashtags_str': initial_hashtags}
        )

    return render(request, 'posts/post_form.html', {
        'form': form,
        'post': post
    })


@login_required
def post_delete_view(request, pk):
    """게시글을 삭제하는 뷰"""
    post = get_object_or_404(Post, pk=pk)
    
    if post.user != request.user:
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('posts:post_detail', pk=pk)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, '게시글이 성공적으로 삭제되었습니다.')
        return redirect('posts:post_list')
    
    return render(request, 'posts/post_detail.html', {'post': post})


class PostListCreateAPIView(generics.ListCreateAPIView):
    """게시글 목록 조회 및 생성 API 뷰"""
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """게시글 상세 조회, 수정 및 삭제 API 뷰"""
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)