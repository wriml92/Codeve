from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PostForm
from .models import Post
from rest_framework import generics, permissions
from .serializers import PostSerializer

# 게시글 목록을 표시
def post_list_view(request):
    posts = Post.objects.all()
    context = {
        'posts': posts
    }
    return render(request, 'posts/post_list.html', context)

# 새로운 게시글을 생성
@login_required
def post_create_view(request):
    if request.method == 'POST':
        form = PostForm(
            data=request.POST,
            files=request.FILES,
            user=request.user
        )
        # 게시글 정보 등록
        if form.is_valid():
            form.save()
            messages.success(request, '게시글이 성공적으로 등록되었습니다.')
            return redirect('posts:post_list')
    else:
        form = PostForm()

    context = {
        'form': form
    }
    return render(request, 'posts/post_form.html', context)

# 게시글의 상세 정보를 표시
@login_required
def post_detail_view(request, pk):
    # 게시글 조회 및 조회수 증감
    post = get_object_or_404(Post, pk=pk)
    post.views += 1
    post.save()
    
    context = {
        'post': post
    }
    return render(request, 'posts/post_detail.html', context)

# 게시글 정보를 수정 
@login_required
def post_update_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 작성자 확인
    if post.user != request.user:
        messages.error(request, '수정 권한이 없습니다.')
        return redirect('posts:post_detail', pk=pk)
    # 기존 게시글 데이터를 폼에 전달
    if request.method == 'POST':
        form = PostForm(
            data=request.POST,
            files=request.FILES,
            instance=post
        )
        # 게시글 정보 수정
        if form.is_valid():
            form.save()
            messages.success(request, '게시글이 성공적으로 수정되었습니다.')
            return redirect('posts:post_detail', pk=pk)
    else:
        # 기존 해시태그를 초기값으로 설정
        initial_hashtags = ' '.join(ht.name for ht in post.hashtags.all())
        form = PostForm(
            instance=post,
            initial={'hashtags_str': initial_hashtags}
        )

    context = {
        'form': form,
        'post': post
    }
    return render(request, 'posts/post_form.html', context)

@login_required
def post_delete_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 작성자 확인
    if post.user != request.user:
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('posts:post_detail', pk=pk)
    
    # 게시글 삭제 
    if request.method == 'POST':
        post.delete()
        messages.success(request, '게시글이 성공적으로 삭제되었습니다.')
        return redirect('posts:post_list')
    
    context = {
        'post': post
    }
    return render(request, 'posts/post_detail.html', context)

# 게시글 목록 조회 및 생성
class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# 게시글 상세 조회, 수정 및 삭제
class PostRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
