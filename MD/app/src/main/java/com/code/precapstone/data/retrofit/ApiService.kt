package com.code.precapstone.data.retrofit

import com.code.precapstone.data.response.InflationResponse
import retrofit2.Call
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST

interface ApiService {
    @FormUrlEncoded
    @POST("/predict")
    fun predict(
        @Field("city") city: String,
        @Field("goal") goal: Float,
        @Field("income") income: Float,
        @Field("expenses") expenses: Float
    ): Call<InflationResponse>
}