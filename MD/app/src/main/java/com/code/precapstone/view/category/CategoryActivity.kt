package com.code.precapstone.view.category

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.code.precapstone.databinding.ActivityCategoryBinding
import com.code.precapstone.view.calculation.CalculationActivity
import com.code.precapstone.view.main.MainActivity

class CategoryActivity : AppCompatActivity() {
    private lateinit var binding: ActivityCategoryBinding
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCategoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.tvBack.setOnClickListener{
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        }

        binding.apply {

            binding.cvCategory1.setOnClickListener{
                val intent = Intent(this@CategoryActivity, CalculationActivity::class.java)
                startActivity(intent)
            }
            binding.cvCategory2.setOnClickListener{
                val intent = Intent(this@CategoryActivity, CalculationActivity::class.java)
                startActivity(intent)
            }
            binding.cvCategory3.setOnClickListener{
                val intent = Intent(this@CategoryActivity, CalculationActivity::class.java)
                startActivity(intent)
            }
            binding.cvCategory4.setOnClickListener{
                val intent = Intent(this@CategoryActivity, CalculationActivity::class.java)
                startActivity(intent)
            }
            binding.cvCategory5.setOnClickListener{
                val intent = Intent(this@CategoryActivity, CalculationActivity::class.java)
                startActivity(intent)
            }
        }
    }
}