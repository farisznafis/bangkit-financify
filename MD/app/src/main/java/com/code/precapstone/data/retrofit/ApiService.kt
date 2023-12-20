package com.code.precapstone.data.retrofit

import com.code.precapstone.data.response.InflationResponse
import retrofit2.Call
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET

interface ApiService {
    @FormUrlEncoded
    @GET("/predict")
    fun predict(
        @Field("city") city: String,
        @Field("goal") goal: Double,
        @Field("income") income: Double,
        @Field("expenses") expenses: Double
    ): Call<InflationResponse>
}