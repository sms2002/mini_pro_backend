from time import time
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import generics, status
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from core.getkeywords import get_top_keywords
from collections import Counter

from technicalquestions_api.models import QuizQuestion, ResultTest,TimeElapsed
from technicalquestions_api.api.serializers import QuizQuestionSerializer, ResultTestSerializer
from authentication.models import User

import json
from random import sample
from collections import defaultdict

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import random
from django.http import Http404
from datetime import datetime

from django.utils import timezone





class QuizQuestionViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated,IsAdminUser]
    serializer_class = QuizQuestionSerializer
    queryset = QuizQuestion.objects.all() 

class GenerateTechnicalQuestionsView(APIView):
    permission_classes = [IsAuthenticated,IsAdminUser]
    def post(self, request):
        try:
            user_name= request.data['username']
        except KeyError:
            return Response({'error': 'No username field'}, status=status.HTTP_400_BAD_REQUEST)
        # Get all questions from the database grouped by subject
        questions_by_subject = defaultdict(list)
        for question in QuizQuestion.objects.all():
            questions_by_subject[question.subject].append(question)

        # Select 10 random questions for each subject
        questions = []
        for subject, subject_questions in questions_by_subject.items():
            questions += sample(subject_questions, 10)

        # Serialize the questions data to JSON
        data = [{
            'question_id': question.question_id,
            'index': count+1,
            'topic': question.topic,
            'question': question.question,
            'option_a': question.option_a,
            'option_b': question.option_b,
            'option_c': question.option_c,
            'option_d': question.option_d,
            'correct_answer': question.correct_answer,
            'difficulty': question.difficulty,
            'cognitive_level': question.cognitive_level,
            'subject': question.subject,
        } for count,question in enumerate(questions)]

        # Return the questions data in a JSON response
        try:
            user = User.objects.get(username=user_name)
        except:
            return Response({'error': 'No user exists'}, status=status.HTTP_400_BAD_REQUEST)
            

# create and save the ResultTest object
        test_time = TimeElapsed(user=user)
        test_time.save()
        
        
        return Response(data)
    

class SimilarQuestionsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    
    def post(self, request):
        try:
            user_name = request.data['username']
        except KeyError:
            return Response({'error': 'No username field'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the latest entry for the specified username

        try_final_tests = ResultTest.objects.filter(user__username=user_name)
        
        if not try_final_tests:
            return Response({'error': 'No ResultTest found for the specified username'}, status=status.HTTP_404_NOT_FOUND)

        wrong_question_ids_counter = Counter()
        top_wrong_question_ids = []

        for result_test in try_final_tests:
            total_score = result_test.results["scores"].get("total_score", 0)
            if total_score < 40:
                for user_response in result_test.results["user_responses"]:
                    question_id = user_response["question_id"]
                    if question_id not in wrong_question_ids_counter:
                        wrong_question_ids_counter[question_id] = 0
                    if user_response["correct_answer"] != user_response["user_answer"]:
                        wrong_question_ids_counter[question_id] += 1
        
        if sum(wrong_question_ids_counter.values())==0:
            return Response({'error': 'No Weak Areas'}, status=status.HTTP_404_NOT_FOUND)
            

        # Retrieve the top 5 wrong question IDs from each subject
        subject_ranges = {
            "OS": range(1, 101),
            "CN": range(101, 201),
            "DBMS": range(201, 301),
            "OOPS": range(301, 401)
        }

        for subject, subject_range in subject_ranges.items():
            subject_wrong_question_ids = [
                question_id for question_id in wrong_question_ids_counter
                if question_id in subject_range and wrong_question_ids_counter[question_id] >= 1
            ]
            subject_top_wrong_question_ids = sorted(subject_wrong_question_ids, key=lambda x: wrong_question_ids_counter[x], reverse=True)[:5]
            top_wrong_question_ids.extend(subject_top_wrong_question_ids)

        # Sort the wrong question IDs based on their counts
        top_wrong_question_ids = sorted(top_wrong_question_ids, key=lambda x: wrong_question_ids_counter[x], reverse=True)

        # Add remaining top frequency elements from other subjects if needed
        remaining_count = 20 - len(top_wrong_question_ids)
        if remaining_count > 0:
            remaining_subjects = [subject for subject in subject_ranges if subject not in subject_ranges]
            for subject in remaining_subjects:
                subject_wrong_question_ids = [
                    question_id for question_id in wrong_question_ids_counter
                    if question_id not in top_wrong_question_ids and question_id in subject_ranges[subject]
                ]
                subject_top_wrong_question_ids = sorted(subject_wrong_question_ids, key=lambda x: wrong_question_ids_counter[x], reverse=True)
                subject_top_wrong_question_ids = [
                    question_id for question_id in subject_top_wrong_question_ids
                    if question_id not in top_wrong_question_ids
                ][:remaining_count]
                top_wrong_question_ids.extend(subject_top_wrong_question_ids)
                remaining_count = 20 - len(top_wrong_question_ids)
                if remaining_count <= 0:
                    break

        
        
        # wrong_question_ids_counter = Counter()
        print(wrong_question_ids_counter)
        for i in wrong_question_ids_counter:
            if len(top_wrong_question_ids)<20:
                if wrong_question_ids_counter[i]>=1 and i not in top_wrong_question_ids:
                    top_wrong_question_ids.append(i)
            else:
                break
                 
            
            
        
        print(top_wrong_question_ids)
        
        #print(result_test.results["user_responses"])
        wrong_question_ids=top_wrong_question_ids

        # Continue with your code using the `result_test` object
        
    #     return Response({'result_test_id': result_test.id}, status=status.HTTP_200_OK)

    # # def post(self, request):
    #     # Get list of wrong question ids from request body
    #     body_unicode = request.body.decode('utf-8')
    #     body = json.loads(body_unicode)
    #     wrong_question_ids = body.get('ids', [])
        # invalid_ids = set(wrong_question_ids) - set(QuizQuestion.objects.values_list('question_id', flat=True))
        # if invalid_ids:
        #     raise Http404(f'Invalid question ids: {", ".join(map(str, invalid_ids))}')

        # Get all questions except the ones the user attempted wrong
        ex_questions = QuizQuestion.objects.filter(question_id__in=wrong_question_ids)
        questions = QuizQuestion.objects.exclude(question_id__in=wrong_question_ids)

        # Create a matrix of the question features (topic, subject, difficulty, cognitive level)
        feature_matrix = []
        ex_feature_matrix = []
        subjects = {}
        for question in questions:
            features = [get_top_keywords(question.question) ,get_top_keywords(question.option_a), get_top_keywords(question.option_b), get_top_keywords(question.option_c), get_top_keywords(question.option_d),
                        question.difficulty, question.cognitive_level, question.subject,question.topic]
            feature_matrix.append(features)
            subject = question.subject
            if subject not in subjects:
                subjects[subject] = [question]
            else:
                subjects[subject].append(question)

        for question in ex_questions:
            features = [get_top_keywords(question.question) ,get_top_keywords(question.option_a), get_top_keywords(question.option_b), get_top_keywords(question.option_c), get_top_keywords(question.option_d),
                        question.difficulty, question.cognitive_level, question.subject,question.topic]
            ex_feature_matrix.append(features)

        # Create a dictionary to store the most similar questions
        similar_questions_dict = {}

        # Calculate the TF-IDF matrix
        tfidf_vectorizer = TfidfVectorizer()
        feature_matrix_tfidf = tfidf_vectorizer.fit_transform([','.join(map(str, row)) for row in feature_matrix])
        ex_feature_matrix_tfidf = tfidf_vectorizer.transform([','.join(map(str, row)) for row in ex_feature_matrix])

        # Calculate the cosine similarity matrix
        similarities = cosine_similarity(ex_feature_matrix_tfidf, feature_matrix_tfidf)

        #Find the 10 most similar questions for each subject
        # for i in range(similarities.shape[0]):
        #     sorted_indices = similarities[i].argsort()[::-1][:40]
        #     for index in sorted_indices:
        #         question = questions[int(index)] 
        #         subject = question.subject
        #         if subject not in similar_questions_dict:
        #             similar_questions_dict[subject] = [question]
        #         elif len(similar_questions_dict[subject]) < 10:
        #             similar_questions_dict[subject].append(question)
                    
                    
        # for i in range(similarities.shape[0]):
        #     sorted_indices = similarities[i].argsort()[::-1][:40]
        #     for index in sorted_indices:
        #         question = questions[int(index)] 
        #         subject = question.subject
        #         if subject not in similar_questions_dict:
        #             similar_questions_dict[subject] = []
        #         if question not in similar_questions_dict[subject]:
        #             similar_questions_dict[subject].append(question)
        #             if len(similar_questions_dict[subject]) >= 10:
        #                 break            

        # Return the similar questions as JSON
        # similar_questions_data = {}
        # for subject in subjects:
        #     subject_questions = similar_questions_dict.get(subject, [])
        #     if len(subject_questions) < 10:
        #         remaining_questions = subjects[subject][:10 - len(subject_questions)]
        #         subject_questions.extend(remaining_questions)
        #     subject_data = QuizQuestionSerializer(subject_questions, many=True).data
        #     similar_questions_data[subject] = subject_data

        # return JsonResponse(similar_questions_data)
        for i in range(similarities.shape[0]):
            sorted_indices = similarities[i].argsort()[::-1][:40]
            for index in sorted_indices:
                question = questions[int(index)] 
                subject = question.subject
                if subject not in similar_questions_dict:
                    similar_questions_dict[subject] = set([question])
                elif len(similar_questions_dict[subject]) < 10:
                    similar_questions_dict[subject].add(question)

        # Create a list of 10 unique questions for each subject
        similar_questions_data = {}
        for subject in subjects:
            subject_questions = list(similar_questions_dict.get(subject, set()))
            if len(subject_questions) < 10:
                remaining_questions = list(set(subjects[subject]) - set(subject_questions))
                subject_questions.extend(remaining_questions[:10 - len(subject_questions)])
            subject_data = QuizQuestionSerializer(subject_questions, many=True).data
            similar_questions_data[subject] = subject_data
            
        final_questions_data = []
        index = 1

        for sublist in similar_questions_data.values():
            for question in sublist:
                question_with_index = {**question, "index": index}
                final_questions_data.append(question_with_index)
                index += 1  
        
        try:
            user_name= request.data['username']
        except KeyError:
            return Response({'error': 'No username field'}, status=status.HTTP_400_BAD_REQUEST)
        # Get all questions from the database grouped by subject
        questions_by_subject = defaultdict(list)
        for question in QuizQuestion.objects.all():
            questions_by_subject[question.subject].append(question)

        # Select 10 random questions for each subject
        questions = []
        for subject, subject_questions in questions_by_subject.items():
            questions += sample(subject_questions, 10)

        # Serialize the questions data to JSON
        data = [{
            'question_id': question.question_id,
            'index': count+1,
            'topic': question.topic,
            'question': question.question,
            'option_a': question.option_a,
            'option_b': question.option_b,
            'option_c': question.option_c,
            'option_d': question.option_d,
            'correct_answer': question.correct_answer,
            'difficulty': question.difficulty,
            'cognitive_level': question.cognitive_level,
            'subject': question.subject,
        } for count,question in enumerate(questions)]

        # Return the questions data in a JSON response
        try:
            user = User.objects.get(username=user_name)
        except:
            return Response({'error': 'No user exists'}, status=status.HTTP_400_BAD_REQUEST)
            

# create and save the ResultTest object
        test_time = TimeElapsed(user=user)
        test_time.save()
        
        return JsonResponse(final_questions_data,safe=False)




    

class ProvideQuestionsView(APIView):
    permission_classes = [IsAuthenticated,IsAdminUser]

    def post(self, request):
        # Get list of wrong question ids from request body
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        question_ids = body.get('ids', [])

        # Get all questions except the ones the user attempted wrong
        questions = QuizQuestion.objects.filter(question_id__in=question_ids)
        #print(questions)
        data = []
        for question in questions:
            data.append({
                'question_id': question.question_id,
                'topic': question.topic,
                'question': question.question,
                'options': [
                    question.option_a,
                    question.option_b,
                    question.option_c,
                    question.option_d,
                ],
                'correct_answer': question.correct_answer,
                'difficulty': question.difficulty,
                'cognitive_level': question.cognitive_level,
                'subject': question.subject,
            })
        return JsonResponse({'questions': data})    
        
        
class ResultTestListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated,IsAdminUser]
    serializer_class = ResultTestSerializer

    def get_queryset(self):
        # print(self.request.user)
        return ResultTest.objects.all()

    # def post(self, request, *args, **kwargs):
    #     serializer = ResultTestSerializer(data=request.data)
    #     if serializer.is_valid():
    #         test = serializer.save()
    #         serializer = ResultTestSerializer(test)
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ResultTestUserView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResultTestSerializer

    def get_queryset(self):
        print(self.request.user)
        return ResultTest.objects.filter(user=self.request.user)
    
class LatestResultTestUserView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResultTestSerializer

    def get_queryset(self):
        user = self.request.user
        latest_results = ResultTest.objects.filter(user=user).order_by('-test_date')[:10]
        return latest_results    
    

class ResultTestUserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResultTestSerializer

    def get_object(self):
        queryset = ResultTest.objects.filter(user=self.request.user)
        obj = get_object_or_404(queryset, pk=self.kwargs.get('pk'))
        return obj
    
    
class UserResponseView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        try:
            question_ids = request.data['ids']
            user_name= request.data['username']
            time_elapsed=request.data['time']
        except KeyError:
            return Response({'error': 'Question IDs not provided'}, status=status.HTTP_400_BAD_REQUEST)
        print(user_name)
        questions = []
        for question_id, user_answer in question_ids.items():
            # if user_answer == 'x':
            #     continue  # User left the question
            question = get_object_or_404(QuizQuestion, pk=question_id)
            questions.append({'question': question, 'user_answer': user_answer})

        correct_count = 0
        total_count = len(questions)
        scores = {}
        subjects = set([q['question'].subject for q in questions])
        for subject in subjects:
            scores[subject] = 0
        for question in questions:
            if question['user_answer'] == question['question'].correct_answer:
                correct_count += 1
                subject = question['question'].subject
                if subject in subjects:
                    scores[subject] += 1

        visualization = {}
        for difficulty in ['easy', 'medium', 'hard']:
            correct = len([q for q in questions if q['question'].difficulty == difficulty and q['user_answer'] == q['question'].correct_answer])
            left = len([q for q in questions if q['question'].difficulty == difficulty and q['user_answer'] == 'x'])
            wrong = len([q for q in questions if q['question'].difficulty == difficulty and q['user_answer'] != q['question'].correct_answer and q['user_answer'] != 'x'])
            
            total = correct + left + wrong
            visualization[f'{difficulty}_correct'] = correct
            visualization[f'{difficulty}_left'] = left
            visualization[f'{difficulty}_wrong'] = wrong
            visualization[f'{difficulty}_total'] = total
            
        for cognitive_level in ['analyzing', 'applying', 'remembering', 'understanding']:
            correct = len([q for q in questions if q['question'].cognitive_level == cognitive_level and q['user_answer'] == q['question'].correct_answer])
            left = len([q for q in questions if q['question'].cognitive_level == cognitive_level and q['user_answer'] == 'x'])
            wrong = len([q for q in questions if q['question'].cognitive_level == cognitive_level and q['user_answer'] != q['question'].correct_answer and q['user_answer'] != 'x'])
            total = correct + left + wrong
            visualization[f'{cognitive_level}_correct'] = correct
            visualization[f'{cognitive_level}_left'] = left
            visualization[f'{cognitive_level}_wrong'] = wrong    
            visualization[f'{cognitive_level}_total'] = total
         
        for subject in ['OS', 'CN', 'DBMS', 'OOPS']:
            correct = len([q for q in questions if q['question'].subject == subject and q['user_answer'] == q['question'].correct_answer])
            left = len([q for q in questions if q['question'].subject == subject and q['user_answer'] == 'x'])
            wrong = len([q for q in questions if q['question'].subject == subject and q['user_answer'] != q['question'].correct_answer and q['user_answer'] != 'x'])
            total = correct + left + wrong
            visualization[f'{subject}_correct'] = correct
            visualization[f'{subject}_left'] = left
            visualization[f'{subject}_wrong'] = wrong    
            visualization[f'{subject}_total'] = total      
            

        scores['total_score'] = correct_count
        #visualization.update(scores)

        result = {
            'user_responses': [{'question_id': q['question'].question_id, 'correct_answer': q['question'].correct_answer, 'user_answer': q['user_answer'] ,"question":q["question"].question,"option_a":q["question"].option_a,"option_b":q["question"].option_b,"option_c":q["question"].option_c,"option_d":q["question"].option_d,"difficulty":q["question"].difficulty,"cognitive_level":q["question"].cognitive_level,"subject":q["question"].subject,"index":ctr+1} for ctr,q in enumerate(questions)],
            'scores': scores,
            'visualization': visualization,
            'time':time_elapsed
        }
        
        user = User.objects.get(username=user_name)

# create and save the ResultTest object
        result_test = ResultTest(user=user, results=result)
        result_test.save()

        result_test_id = result_test.id

        return Response({'results': result, 'id': result_test_id}, status=status.HTTP_200_OK)
    
class TimeResponseView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        try:
            user_name = request.data['username']
        except KeyError:
            return Response({'error': 'No username field'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = TimeElapsed.objects.filter(user__username=user_name).latest('test_date_start')
        except TimeElapsed.DoesNotExist:
            return Response({'error': 'No user exists'}, status=status.HTTP_400_BAD_REQUEST)

        starting_time = user.test_date_start
        current_time = datetime.now(timezone.utc)

        time_difference = current_time - starting_time

        return Response({"time_difference": str(time_difference)})
    
