from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum
from .models import Category, Transaction
from .serializers import (
    UserSerializer, RegisterSerializer,
    CategorySerializer, TransactionSerializer
)


class RegisterView(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Crear categorías por defecto
        default_categories = [
            {'name': 'Salario', 'type': 'income'},
            {'name': 'Freelance', 'type': 'income'},
            {'name': 'Alquiler', 'type': 'expense'},
            {'name': 'Comida', 'type': 'expense'},
            {'name': 'Transporte', 'type': 'expense'},
            {'name': 'Ocio', 'type': 'expense'},
        ]
        
        for cat in default_categories:
            Category.objects.create(user=user, **cat)
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        
        # Filtros opcionales
        category_id = self.request.query_params.get('category', None)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        transaction_type = self.request.query_params.get('type', None)
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if transaction_type:
            queryset = queryset.filter(category__type=transaction_type)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        transactions = self.get_queryset()
        
        income = transactions.filter(category__type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        expense = transactions.filter(category__type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        balance = income - expense
        
        return Response({
            'total_income': float(income),
            'total_expense': float(expense),
            'balance': float(balance),
            'transaction_count': transactions.count()
        })
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        transactions = self.get_queryset().filter(category__type='expense')
        
        categories = {}
        for transaction in transactions:
            cat_name = transaction.category.name
            if cat_name not in categories:
                categories[cat_name] = 0
            categories[cat_name] += float(transaction.amount)
        
        data = [
            {'category': cat, 'amount': amount}
            for cat, amount in categories.items()
        ]
        
        return Response(data)