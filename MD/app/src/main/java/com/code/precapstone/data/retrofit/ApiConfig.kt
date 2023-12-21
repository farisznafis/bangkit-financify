package com.code.precapstone.data.retrofit

import com.code.precapstone.BuildConfig
import okhttp3.OkHttp
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ApiConfig {
    companion object{
        fun getApiService(): ApiService{
            //biar aman sayyyy
            val loggingInterceptor = if(BuildConfig.DEBUG){
                HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BODY)
            }else{
                HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.NONE)
            }

            //buat client nich
            val client = OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .build()

            //buat nge fetch API nya ini nih
            val retrofit = Retrofit.Builder()
                .baseUrl("https://financify-hhof4y5xyq-et.a.run.app") //ganti ini ngab kalo API nya udah dikasi
                .addConverterFactory(GsonConverterFactory.create())
                .client(client)
                .build()

            return retrofit.create(ApiService::class.java)
        }
    }
}