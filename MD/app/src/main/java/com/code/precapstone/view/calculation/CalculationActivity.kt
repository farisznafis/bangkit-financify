package com.code.precapstone.view.calculation

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.code.precapstone.data.response.InflationResponse
import com.code.precapstone.data.retrofit.ApiConfig
import com.code.precapstone.databinding.ActivityCalculationBinding
import com.code.precapstone.view.category.CategoryActivity
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class CalculationActivity : AppCompatActivity() {
    private lateinit var binding: ActivityCalculationBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCalculationBinding.inflate(layoutInflater)
        setContentView(binding.root)


        binding.apply {
            binding.tvBack.setOnClickListener{
                val intent = Intent(this@CalculationActivity, CategoryActivity::class.java)
                startActivity(intent)
            }

            binding.buttonCalculate.setOnClickListener {
                val city = binding.edtCity.text.toString()
                val goal = binding.edtFinancialGoals.text.toString().toFloat()
                val income = binding.edtMonthlyIncome.text.toString().toFloat()
                val expenses = binding.edtMonthlyExpenses.text.toString().toFloat()

                val client = ApiConfig.getApiService().predict(city,goal,income,expenses)
                client.enqueue(object : Callback<InflationResponse>{
                    @SuppressLint("SetTextI18n")
                    override fun onResponse(
                        call: Call<InflationResponse>,
                        response: Response<InflationResponse>
                    ) {
                        if(response.isSuccessful){
                            val prediction = response.body()
                            Log.e("berhasil", "RESULT: ${prediction?.timeRequired?.yearsToGoal}", )
                            binding.tvHasilPrediksiBulan.text = "${prediction?.timeRequired?.yearsToGoal} Tahun ${prediction?.timeRequired?.remainingMonths} Bulan"
                           val trend = prediction?.trend
                            binding.tvTrendInflasi.text = "$trend"

                            when(trend){
                                "up" -> binding.tvTrendInflasi.setTextColor(Color.RED)
                                "down" -> binding.tvTrendInflasi.setTextColor(Color.GREEN)
                                else -> binding.tvTrendInflasi.setTextColor(Color.BLACK)
                            }
                        }else{
                            Log.e("gagal", "RESULT ${response.message()}", )
                        }
                    }

                    override fun onFailure(call: Call<InflationResponse>, t: Throwable) {
                        Log.e("gagal", "onFailure: ${t.message.toString()}", )
                    }

                })

            }
        }
    }
}


